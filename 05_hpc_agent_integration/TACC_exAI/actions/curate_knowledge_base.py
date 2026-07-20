# actions/curate_knowledge_base.py
from .base import Action
from pydantic import BaseModel, Field
from ..utils import display_in_panel, build_default_prompt, build_enum
from ..history_vector_store import HistoryVectorStore
from enum import Enum
import os
import json
from ..json_to_html import render_html_from_json_files  # Import the function

class WikiOperationEnum(str, Enum):
    CREATE = "create"
    EDIT = "edit"
    SEARCH = "search"

class WikiOperationRequest(BaseModel):
    thoughts: str = Field(..., description="Reasoning behind the chosen operation.")
    operation: WikiOperationEnum = Field(..., description="The chosen operation.")

class CreateWikiPageRequest(BaseModel):
    title: str = Field(..., description="Title of the wiki page")
    description: str = Field(..., description="Concise description of the wiki page")
    content: str = Field(..., description="Content of the wiki page")

class SearchWikiPagesRequest(BaseModel):
    query: str = Field(..., description="Search query for wiki pages")

class WikiPage:
    title: str
    description: str

class ChangeType(str, Enum):
    REMOVE = "remove"
    ADD = "add"
    MODIFY = "modify"

class ChangeOperation(BaseModel):
    location_description: str = Field(..., description="Detailed description of the location for the change")
    change_type: ChangeType = Field(..., description="Type of change to apply")
    original_text: str = Field(..., description="Text to remove or modify")
    new_text: str = Field(..., description="New text to add or replace with")

class WikiPageChangeRequest(BaseModel):
    changes: list[ChangeOperation] = Field(..., description="List of changes to apply to the wiki page")

class CurateKnowledgeBaseAction(Action):
    description = "Curate a wiki-style knowledge bases on various topics. Supports creating, editing, and searching wiki pages."
    
    def __init__(self, parent=None, child=None, tracer=None, agent=None):
        super().__init__(parent=parent, child=child, tracer=tracer, agent=agent)
        self.knowledge_base_dir = "knowledge_base"
        os.makedirs(self.knowledge_base_dir, exist_ok=True)
        self.vectorstore_name = "wiki_pages"
        vs_dir = "vectorstores"
        os.makedirs(vs_dir, exist_ok=True)
        vs_path = os.path.join(vs_dir, f"{self.vectorstore_name}.pkl")
        self.wiki_pages_store = HistoryVectorStore(self.vectorstore_name)
        if not os.path.exists(vs_path) or os.path.getsize(vs_path) == 0:
            self.build_wiki_pages_vector_store()
        self.output_folder = "knowledge_base_html"  # Define the output folder

        
    def build_wiki_pages_vector_store(self):
        self.wiki_pages_store.entries = []  # Clear existing entries
        for filename in os.listdir(self.knowledge_base_dir):
            if filename.endswith(".json"):
                try:
                    with open(os.path.join(self.knowledge_base_dir, filename), "r", encoding="utf-8") as f:
                        data = json.load(f)
                    title = data.get("title", "")
                    description = data.get("description", "")
                    content = data.get("content", "")
                    self.wiki_pages_store.add_message("wiki", "title", title)
                    self.wiki_pages_store.add_message("wiki", "description", description)
                    self.wiki_pages_store.add_message("wiki", "content", content)
                except Exception as e:
                    print(f"⚠️ Failed to load {filename}: {e}")
        self.wiki_pages_store._save()  # Save the vector store

    def _run_impl(self, user_input: str, mode: str):
        # Determine the operation based on user input
        prompt = build_default_prompt(
            self.agent,
            task_description="Decide whether the user wants to create, edit, or search for a wiki page based on their input.",
            response_classes=[WikiOperationRequest]
        )
        response: WikiOperationRequest = self.generate_with_schema_action(
            schema=WikiOperationRequest,
            prompt=prompt,
            mode=mode
        )
        if mode == "dev":
            display_in_panel(response, title="Wiki Operation Decision")
        operation = response.operation.value
        if operation == WikiOperationEnum.CREATE:
            if self.tracer:
                with self.tracer.start_as_current_span("Create Wiki", openinference_span_kind="unknown"):
                    self.create_wiki_page(user_input, mode)
            else:
                self.create_wiki_page(user_input, mode)
        elif operation == WikiOperationEnum.EDIT:
            if self.tracer:
                with self.tracer.start_as_current_span("Edit Wiki", openinference_span_kind="unknown"):
                    self.edit_wiki_page(user_input, mode)
            else:
                self.edit_wiki_page(user_input, mode)
        elif operation == WikiOperationEnum.SEARCH:
            if self.tracer:
                with self.tracer.start_as_current_span("Search Wiki", openinference_span_kind="unknown"):
                    self.search_wiki_pages(user_input, mode)
            else:
                self.search_wiki_pages(user_input, mode)
                
        return "success"

    def create_wiki_page(self, user_input: str, mode: str):
        prompt = build_default_prompt(
            self.agent,
            task_description="Create a new wiki page based on the user's request.",
            response_classes=[CreateWikiPageRequest]
        )
        response: CreateWikiPageRequest = self.generate_with_schema_action(
            schema=CreateWikiPageRequest,
            prompt=prompt,
            mode=mode,
        )
        title = response.title
        description = response.description
        content = response.content
        filename = f"{title}.json"
        with open(os.path.join(self.knowledge_base_dir, filename), "w", encoding="utf-8") as f:
            json.dump({"title": title, "description": description, "content": content}, f, indent=2, ensure_ascii=False)
        self.wiki_pages_store.add_message("wiki", "title", title)
        self.wiki_pages_store.add_message("wiki", "description", description)
        self.wiki_pages_store.add_message("wiki", "content", content)
        self.wiki_pages_store._save()  # Save the vector store
        display_in_panel(f"Wiki page '{title}' created successfully.", title="Success")
        render_html_from_json_files(self.knowledge_base_dir, self.output_folder, filename)  # Render HTML

    def edit_wiki_page(self, user_input: str, mode: str):
        wiki_pages = [(f.replace(".json", ""), f.replace(".json", "")) for f in os.listdir(self.knowledge_base_dir) if f.endswith(".json")]
        WikiPageEnum = build_enum(wiki_pages)
        # Define EditWikiPageRequest dynamically with WikiPageEnum
        class EditWikiPageRequest(BaseModel):
            title: WikiPageEnum = Field(..., description="Title of the wiki page to edit")
            changes: WikiPageChangeRequest = Field(..., description="Changes to apply to the wiki page")

        prompt = build_default_prompt(
            self.agent,
            task_description="Edit an existing wiki page based on the user's request.",
            response_classes=[EditWikiPageRequest, WikiPageEnum, WikiPageChangeRequest, ChangeOperation]
        )
        response: EditWikiPageRequest = self.generate_with_schema_action(
            schema=EditWikiPageRequest,
            prompt=prompt,
            mode=mode,
        )
        if mode == "dev":
            display_in_panel(response, title="EditWikiPage Request")
        title = response.title.value
        changes = response.changes.changes
        filename = f"{title}.json"
        if os.path.exists(os.path.join(self.knowledge_base_dir, filename)):
            with open(os.path.join(self.knowledge_base_dir, filename), "r", encoding="utf-8") as f:
                data = json.load(f)
            current_title = data["title"]
            current_description = data["description"]
            current_content = data["content"]
            for change in changes:
                change_prompt = (
                    f"Apply the following change to the wiki page:\n\n"
                    f"**Current Title:** {current_title}\n"
                    f"**Current Description:** {current_description}\n"
                    f"**Current Content:** {current_content}\n\n"
                    f"**Change:**\n"
                    f"Location: {change.location_description}\n"
                    f"Type: {change.change_type.value}\n"
                    f"Original Text: {change.original_text}\n"
                    f"New Text: {change.new_text}\n\n"
                    f"**Task:** Update the wiki page content accordingly."
                )
                class UpdatedWikiPage(BaseModel):
                    updated_content: str = Field(..., description="Updated content of the wiki page")

                updated_response: UpdatedWikiPage = self.generate_with_schema_action(
                    schema=UpdatedWikiPage,
                    prompt=change_prompt,
                    mode=mode
                )
                current_content = updated_response.updated_content
            data["content"] = current_content
            if mode == "dev":
                display_in_panel(current_content, title="New Wiki Content")
            with open(os.path.join(self.knowledge_base_dir, filename), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            self.build_wiki_pages_vector_store()  # Rebuild the vector store
            display_in_panel(f"Wiki page '{title}' updated successfully.", title="Success")
            render_html_from_json_files(self.knowledge_base_dir, self.output_folder, filename)
        else:
            display_in_panel(f"Wiki page '{title}' not found.", title="Error")

    def search_wiki_pages(self, user_input: str, mode: str):
        prompt = build_default_prompt(
            self.agent,
            task_description="Search for wiki pages based on the user's query.",
            response_classes=[SearchWikiPagesRequest]
        )
        response: SearchWikiPagesRequest = self.generate_with_schema_action(
            schema=SearchWikiPagesRequest,
            prompt=prompt,
            mode=mode
        )
        query = response.query
        top_k = 5
        hits = self.wiki_pages_store.search(query, top_k=top_k)
        results = []
        chunk_texts = []
        for i, hit in enumerate(hits):
            chunk_text = hit[1].get("chunk_text", "")
            metadata = hit[1].get("metadata", {})
            wiki_title = metadata.get("title", "")
            description = metadata.get("description", "")
            chunk_texts.append({
                "chunk_text": chunk_text,
                "wiki_title": wiki_title,
                "description": description
            })
            results.append(f"Chunk {i+1}: ```{chunk_text}```")
        display_in_panel("\n\n".join(results), title="Search Results")
        # Perform structured generation to answer the user's query
        class AnswerQueryRequest(BaseModel):
            thoughts: str = Field(..., description="Thoughts on how to answer the user's query based on the retrieved wiki data.")
            answer: str = Field(..., description="A succinct answer to the user's original query.")

        prompt = build_default_prompt(
            self.agent,
            task_description="Answer the user's query based on the retrieved wiki data.",
            response_classes=[AnswerQueryRequest],
            custom_history=None,
            hide_current_summary=False,
            top_k_vector_matches=0  # We're not using vector matches here, so set to 0
        )
        # Add retrieved chunk information to the prompt
        chunk_info = "\n".join(
            f"Chunk {i+1}:\nTitle: {chunk['wiki_title']}\nDescription: {chunk['description']}\nText: ```{chunk['chunk_text']}```\n"
            for i, chunk in enumerate(chunk_texts)
        )
        prompt += f"**Retrieved Wiki Data:**\n{chunk_info}\n\n**User's Original Query:**\n{user_input}\n\n"
        response: AnswerQueryRequest = self.generate_with_schema_action(
            schema=AnswerQueryRequest,
            prompt=prompt,
            mode=mode
        )
        display_in_panel(response.answer, title="Answer")
