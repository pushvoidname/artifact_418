import random
import string
import re
import json
from .counter_factual_utils import rand_num, rand_str


def remove_braces(s: str) -> str:
    """
    convert '\\u{47d}\\u{f197}\\u{b5fb}\\u{f907}' to '\\u047d\\uF197\\uB5FB\\uF907'
    """
    pattern = re.compile(r'\\u\{([0-9A-Fa-f]+)\}')
    
    def repl(m):
        cp_hex = m.group(1)
        cp = int(cp_hex, 16)
        return '\\u%04X' % cp
    
    return pattern.sub(repl, s)


def remove_special_characters(text):
    # Regex pattern matching specified characters
    pattern = r'[,.\[\]{}()\'"<> ]'
    # Remove matched characters and return
    return re.sub(pattern, '', text)

def generate_random_string(length: int) -> str:
    characters = string.ascii_letters + string.digits
    return ''.join(random.choices(characters, k=length))

def generate_printable_string(length: int) -> str:
    characters = string.printable
    return ''.join(random.choices(characters, k=length))


def replace_statement_parameter(return_dict: dict, obj_set: set, hook_code: str) -> dict:
    params = return_dict.get("params", {})
    if not params:
        return return_dict
    obj_list = list(obj_set)  # Convert to list for random.choice compatibility
    if len(obj_list) == 0:
        obj_list = ['this']

    for param_name in params.keys():
        param_value = params[param_name]
        if param_value == '"<<BUILTINOBJ>>"':
            return_dict['params'][param_name] = random.choice(obj_list)
        elif param_value =='"<<SCRIPTS>>"':
            return_dict['params'][param_name] = hook_code
            # param_value = random.choice(obj_list)
    
    # for key in params:
    key = random.choice(list(params.keys()))
    # Determine replacement probability based on key prefix
    replace_prob = 0.4 if key.startswith('o') else 0
    
    # Attempt replacement if set is not empty and probability check passes
    if obj_list and random.random() < replace_prob:
        return_dict['params'][key] = random.choice(obj_list)
            
    return return_dict


def generate_define_properties_code(
    object_properties: list,
    prop_key: str,
    value: str,
    hook_code: str = "",
) -> str:
    # Generate random 4-character hex suffix
    suffix = ''.join(random.choices('abcdef0123456789', k=4))
    
    # Create variable names following original pattern
    f_name = f"f_{suffix}"
    fs_name = f"fs_{suffix}"
    obj_name = f"os_{suffix}"

    # Build code components
    components = [
        f"var {f_name}=function(){{{hook_code}}};",
        # Getter function definition
        f"var {fs_name}=function(){{{f_name}();return {value};}};",
        # Object initialization
        f"var {obj_name}={{{','.join(object_properties)}}};" if object_properties else f"var {obj_name}={{}};",
        # Property definition
        f"Object.defineProperties({obj_name},{{{prop_key}:{{get:{fs_name}}}}});"
    ]
    
    # Combine into single line with proper formatting
    return obj_name, " ".join(components)


def generate_statement_with_object_hook_complex(return_dict: dict, hook_code=""):
    params = return_dict.get("params", {})
    if not params:
        return None, None
    api_type = return_dict.get("api_type")
    if api_type != "method":
        return None, None
    key = random.choice(list(params.keys()))
    value = return_dict['params'][key]

    param_expressions = []
    for key, value in params.items():
        param_expressions.append(f"{key}: {value}")

    os_name, object_generate_statement = generate_define_properties_code(param_expressions, key, value, hook_code)

    instance_name = return_dict.get("instance_name")
    api_name = return_dict.get("api_name", "<unknown_api>")
    return_value = return_dict.get("return_value", "")

    if return_value != "":
        return os_name, f"{object_generate_statement} try{{{return_value} = {instance_name}.{api_name}({os_name});}} catch(e){{}}"
    return os_name, f"{object_generate_statement} try{{{instance_name}.{api_name}({os_name});}} catch(e){{}}"


def generate_statement_with_object_hook_simple(return_dict: dict, hook_code=""):
    params = return_dict.get("params", {})
    if not params:
        return None, None
    key = random.choice(list(params.keys()))

    value = return_dict['params'][key]

    os_name, object_generate_statement = generate_object_with_method(value, hook_code)

    return_dict['params'][key] = os_name

    return os_name, object_generate_statement


def generate_object_with_method(value, hook_code=""):
    suffix = ''.join(random.choices('abcdef0123456789', k=4))
    
    # Generate names
    f_name = f"f_{suffix}"
    fs_name = f"fs_{suffix}"
    os_name = f"os_{suffix}"
    
    # Choose method randomly
    method = random.choice(['toString', 'valueOf'])

    # generate random property for object
    prop_defs = []
    for _ in range(random.randint(1, 3)):
        key = random.choice(['p', 'k', 'x']) + ''.join(random.choices('0123456789', k=random.randint(1, 2)))
        
        val_type = random.choice(['num', 'str', 'bool', 'null'])
        if val_type == 'num':
            val = str(random.choice([0, 1, 123, 0x7fffffff, -1]))
        elif val_type == 'str':
            val = json.dumps(''.join(random.choices('abcdef', k=3)))
        elif val_type == 'bool':
            val = random.choice(['true', 'false'])
        else:
            val = 'null'
        
        prop_defs.append(f"{key}:{val}")
    
    # Build JS code components
    code_parts = [
        f"var {f_name}=function(){{{hook_code}}};",
        f"var {fs_name}=function(){{{f_name}();return {value};}};",
        f"var {os_name}={{{','.join(prop_defs)}}};" if prop_defs else f"var {os_name}={{}};",
        f"{os_name}.{method}={fs_name};"
    ]
    
    # Join into single line
    compact_js = " ".join(code_parts)
    
    return os_name, compact_js


def construct_statement(return_dict: dict) -> str:
    # Extract required fields from the dictionary
    instance_name = return_dict.get("instance_name")
    api_type = return_dict.get("api_type")
    api_name = return_dict.get("api_name", "<unknown_api>")
    params = return_dict.get("params", {})
    return_value = return_dict.get("return_value", "")
    
    if not instance_name or instance_name == "":
        print(f"[X] error when processing {return_dict}")
        return None

    if api_type == "method":
        # If no parameters, return the API call with an empty parameter dictionary.
        if not params:
            if return_value != "":
                return f"var {return_value}; {return_value} = {instance_name}.{api_name}();"
            return f"{instance_name}.{api_name}();"
        
        # Special case: if there is exactly one parameter with key "NoParameterName",
        # return the API call with the value passed directly.
        if len(params) == 1 and "NoParameterName" in params:
            value = params["NoParameterName"]
            if return_value != "":
                return f"var {return_value}; {return_value} = {instance_name}.{api_name}({value});"
            return f"{instance_name}.{api_name}({value});"
        
        # Otherwise, build the API call by joining key:value pairs.
        param_expressions = []
        for key, value in params.items():
            param_expressions.append(f"{key}: {value}")
        joined_params = ", ".join(param_expressions)
        if return_value != "":
            return f"var {return_value}; {return_value} = {instance_name}.{api_name}({{{joined_params}}});"
        return f"{instance_name}.{api_name}({{{joined_params}}});"
    
    elif api_type == "property":
        # If no parameters, return just the API name.
        if not params:
            if return_value != "":
                return f"var {return_value}; {return_value} = {instance_name}.{api_name};"
            return f"{instance_name}.{api_name};"
        
        # For property type, ensure there is exactly one parameter.
        if len(params) != 1:
            raise ValueError("Property type API must have exactly one parameter.")
        
        # Retrieve the single parameter's value (ignoring its key) and return in assignment format.
        value = list(params.values())[0]
        if return_value != "":
            return f"{instance_name}.{api_name} = {value}; var {return_value}; {return_value} = {instance_name}.{api_name};"
        return f"{instance_name}.{api_name} = {value};"
    else:
        # If the API type is unknown, raise an error.
        raise ValueError("Unknown API type.")  
    

def build_statement_from_raw_call(return_dict: dict) -> str:
    api_call_str = construct_statement(return_dict)
    if api_call_str:
        return f"try{{{api_call_str}}} catch(e){{}};"
    return None


def infer_value_type(value: str) -> str:
    value = value.strip()
    
    # Check for array type.
    if value.startswith('[') and value.endswith(']'):
        return 'array'
    
    # Check for object type.
    if value.startswith('{') and value.endswith('}'):
        return 'object'
    
    # Check for boolean type.
    if value == "true" or value == "false":
        return 'boolean'
    
    # Check for number type.
    def is_number(s: str) -> bool:
        """
        Check if the string represents a valid number.
        A valid number must have:
        - An optional leading '-' sign.
        - At least one digit.
        - At most one '.' character.
        """
        if not s:
            return False

        if s[0] == '-':
            s = s[1:]
            if not s:
                return False

        dot_count = 0
        has_digit = False
        for char in s:
            if char.isdigit():
                has_digit = True
            elif char == '.':
                dot_count += 1
                if dot_count > 1:
                    return False
            else:
                return False
        return has_digit


    if is_number(value):
        return 'number'
    
    return 'string'


def parse_array_elements(s: str) -> list:
    elements = []
    current = []       # Accumulate characters for the current element.
    bracket_level = 0  # Level for nested brackets/braces.
    in_quotes = False  # Whether we are inside double quotes.
    escape = False     # Whether the current character is escaped.

    for char in s:
        if escape:
            current.append(char)
            escape = False
            continue

        if char == '\\':
            escape = True
            current.append(char)
            continue

        if char == '"':
            in_quotes = not in_quotes
            current.append(char)
            continue

        if not in_quotes:
            if char in ['[', '{']:
                bracket_level += 1
            elif char in [']', '}']:
                bracket_level -= 1

            # Split on comma only if at the top level.
            if char == ',' and bracket_level == 0:
                element = ''.join(current).strip()
                elements.append(element)
                current = []
                continue

        current.append(char)

    if current:
        element = ''.join(current).strip()
        if element:
            elements.append(element)

    return elements


def parse_object_members(s: str) -> list:
    members = []
    current = []       # Accumulate characters for the current member.
    bracket_level = 0  # Counter for nested structures.
    in_quotes = False  # Flag for being inside double quotes.
    escape = False     # Flag for escaping characters.

    # First, split the object members by comma at the top level.
    for char in s:
        if escape:
            current.append(char)
            escape = False
            continue

        if char == '\\':
            escape = True
            current.append(char)
            continue

        if char == '"':
            in_quotes = not in_quotes
            current.append(char)
            continue

        if not in_quotes:
            if char in ['{', '[']:
                bracket_level += 1
            elif char in ['}', ']']:
                bracket_level -= 1

            if char == ',' and bracket_level == 0:
                member = ''.join(current).strip()
                if member:
                    members.append(member)
                current = []
                continue

        current.append(char)

    if current:
        member = ''.join(current).strip()
        if member:
            members.append(member)

    # Now, split each member into key and value using the first colon at the top level.
    result = []
    for member in members:
        colon_index = None
        bracket_level = 0
        in_quotes = False
        escape = False

        for i, char in enumerate(member):
            if escape:
                escape = False
                continue
            if char == '\\':
                escape = True
                continue
            if char == '"':
                in_quotes = not in_quotes
                continue
            if not in_quotes:
                if char in ['{', '[']:
                    bracket_level += 1
                elif char in ['}', ']']:
                    bracket_level -= 1
                if char == ':' and bracket_level == 0:
                    colon_index = i
                    break

        if colon_index is not None:
            key = member[:colon_index].strip()
            value_part = member[colon_index + 1:].strip()
        else:
            # If no colon is found, treat the entire member as the key with an empty value.
            key = member.strip()
            value_part = ""

        result.append((key, value_part))
    return result


def normalize_generated_value(value: str) -> str:
    inferred_type = infer_value_type(value)

    p_counter_factual = random.random()

    if inferred_type == 'string':
        # small chance to replace with counter factual string
        if p_counter_factual < 0.01:
            value = rand_str()
            return value
            # normalized_content = ""
            # for char in value:
            #     if char in ('{', '}'):
            #         normalized_content += ""
            #     else:
            #         normalized_content += char
            # return normalized_content
        # Remove existing wrapping quotes, if any.
        if value.startswith('"') and value.endswith('"'):
            content = value[1:-1]
        else:
            content = value

        # Escape double quotes and backslashes in the content.
        normalized_content = ""
        for char in content:
            if char in ('"', '\\', '\n', '\r', "(", ")"):
                normalized_content += ""
            else:
                normalized_content += char

        return f'"{normalized_content}"'

    elif inferred_type == 'array':
        # Remove the outer square brackets.
        content = value[1:-1].strip()
        if not content:
            return "[]"
        # Parse and normalize each array element.
        elements = parse_array_elements(content)
        normalized_elements = [normalize_generated_value(elem) for elem in elements]
        return "[" + ", ".join(normalized_elements) + "]"

    elif inferred_type == 'object':
        # Remove the outer curly braces.
        content = value[1:-1].strip()
        if not content:
            return "{}"
        # Parse the object members into key-value pairs.
        members = parse_object_members(content)
        normalized_pairs = []

        for key, val in members:
            # Normalize the key.
            # Remove existing quotes if present.
            if key.startswith('"') and key.endswith('"'):
                key_content = key[1:-1]
            else:
                key_content = key

            # If the key does not start with an alphabet letter, prepend a random letter.
            if key_content and not key_content[0].isalpha():
                random_letter = random.choice(string.ascii_letters)
                key_content = random_letter + key_content

            # Escape double quotes and backslashes in the key.
            escaped_key = ""
            for char in key_content:
                if char in ('"', '\\', '\n', '\r', "(", ")"):
                    escaped_key += ''
                else:
                    escaped_key += char
            normalized_key = f'"{escaped_key}"'

            # Normalize the value recursively.
            normalized_value = normalize_generated_value(val)
            normalized_pairs.append(f"{normalized_key}: {normalized_value}")

        return "{" + ", ".join(normalized_pairs) + "}"

    elif inferred_type == 'number':
        # small chance to replace with counter factual number
        if p_counter_factual < 0.01:
            value = rand_num()
            return value
        
        # handle octal
        if len(value) > 2 and value[1] in ('o', 'O', 'b', 'B'):
            value[1] = '9'
            value = value[1:]
        
        # Remove all leading zeros from the number while preserving sign and fractional part.
        sign = ""
        num_str = value

        if num_str.startswith("-"):
            sign = "-"
            num_str = num_str[1:]

        if "." in num_str:
            int_part, frac_part = num_str.split(".", 1)
            int_part = int_part.lstrip("0")
            if int_part == "":
                int_part = "0"
            return sign + int_part + "." + frac_part
        else:
            num_str = num_str.lstrip("0")
            if num_str == "":
                num_str = "0"
            return sign + num_str

    # For booleans, return the value unchanged.
    return value
