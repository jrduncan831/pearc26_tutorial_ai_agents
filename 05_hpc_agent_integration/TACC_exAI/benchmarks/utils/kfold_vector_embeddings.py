import pandas as pd
from sklearn.model_selection import GroupKFold
import numpy as np
import json
import argparse
import sys
import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple
from sentence_transformers import SentenceTransformer
import pickle 

import sys
import os
from history_vector_store import recursive_chunk

# split metadata columns into multiple columns 
def expand_dict_column(df, col_name, prefix=None):
    """
    df: pandas DataFrame
    col_name: name of the column containing dictionaries
    prefix: optional prefix for new column names
    """
    # Turn dicts into a DataFrame (each key becomes a column)
    expanded = df[col_name].apply(pd.Series)

    # Optionally add a prefix to avoid name clashes
    if prefix:
        expanded = expanded.add_prefix(prefix)

    # Join back to original df
    return pd.concat([df.drop(columns=[col_name]), expanded], axis=1)

def create_folds(n_splits, path_to_experiments):
    # read experiment_runs.json from specified path
    merged_df = pd.read_json(path_to_experiments)
        
    # get additional columns needed in DF
    df_new = expand_dict_column(merged_df, "metadata")
    
    # perform k folds splits
    gkf = GroupKFold(n_splits=n_splits)
    groups = df_new["file_name"].values
    folds = {fold: val_idx.tolist() for fold, (_, val_idx) in enumerate(gkf.split(df_new, groups=groups))}
    return folds,df_new

def create_and_write_folds(folds,embedding_model,df_new, path_to_write, max_chunk_size):
    model = SentenceTransformer(embedding_model)
    for fold,indices in folds.items():
        entries = []
        for index in indices:
            content= df_new.input[index]['prompt']
            chunks = recursive_chunk(content, max_size=max_chunk_size)
            for idx, chunk in enumerate(chunks):
                embedding = model.encode(chunk, normalize_embeddings=True)
                entry = {
                        "trace_id": df_new.trace_id[index],
                        "problem_id": index,
                        "orig_content": df_new.input[index]['prompt'],
                        "result": df_new.result[index],
                        "chunk_index": idx,
                        "chunk_text": chunk,
                        "embedding": embedding
                    }
            entries.append(entry)
        # write file 
        file_name = os.path.join(path_to_write, f'question_fold_{fold}.pkl')
        with open(file_name, "wb") as f:
                pickle.dump(entries, f, protocol=pickle.HIGHEST_PROTOCOL)
    # write small dictionary with problem ids in each fold; plan to injest this into benchmark to point 
    # to what fold should be used in RAG for each problem id
    with open("folds.json", "w") as f:
        json.dump(folds, f)

def main():
    parser = argparse.ArgumentParser(description="Create question folds and write embeddings to disk.")
    parser.add_argument("--n_splits", type=int, default=5, help="Number of folds for cross-validation.")
    parser.add_argument("--path_to_experiments", type=Path, default="experiment_runs.json", help="Path to experiment JSON file.")
    parser.add_argument("--max_chunk_size", type=int, default=250, help="Maximum size of text chunks.")
    parser.add_argument("--path_to_write", type=str, default=".", help="Directory to save output pickle files.")
    parser.add_argument("--embedding_model", type=str, default="all-MiniLM-L6-v2", help="SentenceTransformer model name.")

    args = parser.parse_args()

    folds, df_new = create_folds(args.n_splits, args.path_to_experiments)
    create_and_write_folds(
        folds=folds,
        embedding_model=args.embedding_model,
        df_new=df_new,
        path_to_write=Path(args.path_to_write),
        max_chunk_size=args.max_chunk_size
    )

if __name__ == "__main__":
    main()
    
