
import inspect
import json

def trace_method(tracer, method, span_name,openinference_span_kind):
    def is_valid_type(value):
        valid_types = (bool, int, float, str)
        if isinstance(value, valid_types):
            return True
        if isinstance(value, (list, tuple)):
            return all(isinstance(v, valid_types) for v in value)
        return False

    def safe_set_attribute(span, key, value):
        try:
            if is_valid_type(value):
                span.set_attribute(key, value)
            else:
                span.set_attribute(key, str(value))
        except Exception as e:
            span.set_attribute(f"{key}_error", str(e))

    def wrapper(*args, **kwargs):
        with tracer.start_as_current_span(span_name,openinference_span_kind=openinference_span_kind) as span:
            sig = inspect.signature(method)
            param_names = list(sig.parameters.keys())

            for name, value in zip(param_names, args):
                safe_set_attribute(span, name, value)

            for k, v in kwargs.items():
                safe_set_attribute(span, k, v)

            result = method(*args, **kwargs)
            try:
                result_dict = result.dict() if hasattr(result, "dict") else result
                result_json = json.dumps(result_dict, ensure_ascii=False)
                safe_set_attribute(span, "result", result_json)
            except Exception as e:
                safe_set_attribute(span, "result_error", str(e))

            return result

    return wrapper


