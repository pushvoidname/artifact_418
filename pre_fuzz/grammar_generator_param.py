import os
import json
import logging
from typing import Dict, Any, List, Optional
from utils.util import load_objects_description
from pathlib import Path
import argparse
from agentlib import OpenAIHandler, AnthropicHandler, UnsupportedModelError
import re


# Configure logging
logging.basicConfig(
    filename='llm_chat_parameter_grammar_generator.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

grammar_generation_agent = None
return_type_agent = None
parameter_condition_agent = None

def generate_grammar_for_parameter(api_info: Dict[str, Any], param_name: str, param_details: Any) -> Any:
    api_type = api_info.get('API_Type', '').lower()
    object_name = api_info.get('Object', '')
    api_name = api_info.get('API_Name', '')
    api_description = api_info.get('API_Description', '')

    # Construct a prompt specifically for a single parameter
    if api_type == 'method':
        # Prompt for Method API parameter
        prompt = (
            f"Generate a context-free grammar in JSON format for the parameter '{param_name}' "
            f"of the following Method API. The grammar should follow these rules:\n"
            "1. This grammar should only focus on the specified parameter.\n"
            "2. Provide a JSON array of rules that defines how to parse this parameter.\n"
            "3. The value should respect the parameter's type if known (e.g., string, boolean, number).\n\n"
            "API Information:\n"
            f"Object: {object_name}\n"
            f"API_Name: {api_name}\n"
            f"API_Type: {api_type}\n"
            f"API_Description: {api_description}\n"
            "Parameter Details:\n"
            f"{json.dumps({param_name: param_details}, indent=2)}\n\n"
            "Sample JSON Grammar (for reference):\n"
            "[\n"
            '    ["PARAM_VALUE", "[ {NUMBER}, \"{STRING}\", {BOOLEAN} ]"],\n'
            '    ["NUMBER", "{INTEGER}"],\n'
            '    ["NUMBER", "{DECIMAL}"],\n'
            '    ["INTEGER", "{SIGN}{DIGIT_SEQUENCE}"],\n'
            '    ["DECIMAL", "{SIGN}{DIGIT_SEQUENCE}.{DIGIT_SEQUENCE}"],\n'
            '    ["SIGN", ""],\n'
            '    ["SIGN", "-"],\n'
            '    ["DIGIT_SEQUENCE", "{DIGIT}"],\n'
            '    ["DIGIT_SEQUENCE", "{DIGIT}{DIGIT_SEQUENCE}"],\n'
            '    ["DIGIT", "0"],\n'
            '    ["DIGIT", "1"],\n'
            '    ["DIGIT", "2"],\n'
            '    ["DIGIT", "3"],\n'
            '    ["DIGIT", "4"],\n'
            '    ["DIGIT", "5"],\n'
            '    ["DIGIT", "6"],\n'
            '    ["DIGIT", "7"],\n'
            '    ["DIGIT", "8"],\n'
            '    ["DIGIT", "9"],\n'
            '    ["STRING", "{FIELD_TYPE}"],\n'
            '    ["FIELD_TYPE", "text"],\n'
            '    ["FIELD_TYPE", "button"],\n'
            '    ["FIELD_TYPE", "combobox"],\n'
            '    ["FIELD_TYPE", "listbox"],\n'
            '    ["FIELD_TYPE", "checkbox"],\n'
            '    ["FIELD_TYPE", "radiobutton"],\n'
            '    ["FIELD_TYPE", "signature"]\n'
            '    ["STRING", "{FIELD_NAME}"],\n'
            '    ["FIELD_NAME", "{NAME_PART}"],\n'
            '    ["FIELD_NAME", "{NAME_PART}.{FIELD_NAME}"],\n'
            '    ["NAME_PART", "{CHAR}{NAME_PART}"],\n'
            '    ["NAME_PART", "{CHAR}"],\n'
            '    ["CHAR", "a"],\n'
            '    ["CHAR", "b"],\n'
            '    ["CHAR", "c"],\n'
            '    ["CHAR", "d"],\n'
            '    ["CHAR", "e"],\n'
            '    ["CHAR", "f"],\n'
            '    ["CHAR", "g"],\n'
            '    ["CHAR", "h"],\n'
            '    ["CHAR", "i"],\n'
            '    ["CHAR", "j"],\n'
            '    ["CHAR", "k"],\n'
            '    ["CHAR", "l"],\n'
            '    ["CHAR", "m"],\n'
            '    ["CHAR", "n"],\n'
            '    ["CHAR", "o"],\n'
            '    ["CHAR", "p"],\n'
            '    ["CHAR", "q"],\n'
            '    ["CHAR", "r"],\n'
            '    ["CHAR", "s"],\n'
            '    ["CHAR", "t"],\n'
            '    ["CHAR", "u"],\n'
            '    ["CHAR", "v"],\n'
            '    ["CHAR", "w"],\n'
            '    ["CHAR", "x"],\n'
            '    ["CHAR", "y"],\n'
            '    ["CHAR", "z"],\n'
            '    ["CHAR", "A"],\n'
            '    ["CHAR", "B"],\n'
            '    ["CHAR", "C"],\n'
            '    ["CHAR", "D"],\n'
            '    ["CHAR", "E"],\n'
            '    ["CHAR", "F"],\n'
            '    ["CHAR", "G"],\n'
            '    ["CHAR", "H"],\n'
            '    ["CHAR", "I"],\n'
            '    ["CHAR", "J"],\n'
            '    ["CHAR", "K"],\n'
            '    ["CHAR", "L"],\n'
            '    ["CHAR", "M"],\n'
            '    ["CHAR", "N"],\n'
            '    ["CHAR", "O"],\n'
            '    ["CHAR", "P"],\n'
            '    ["CHAR", "Q"],\n'
            '    ["CHAR", "R"],\n'
            '    ["CHAR", "S"],\n'
            '    ["CHAR", "T"],\n'
            '    ["CHAR", "U"],\n'
            '    ["CHAR", "V"],\n'
            '    ["CHAR", "W"],\n'
            '    ["CHAR", "X"],\n'
            '    ["CHAR", "Y"],\n'
            '    ["CHAR", "Z"],\n'
            '    ["CHAR", "0"],\n'
            '    ["CHAR", "1"],\n'
            '    ["CHAR", "2"],\n'
            '    ["CHAR", "3"],\n'
            '    ["CHAR", "4"],\n'
            '    ["CHAR", "5"],\n'
            '    ["CHAR", "6"],\n'
            '    ["CHAR", "7"],\n'
            '    ["CHAR", "8"],\n'
            '    ["CHAR", "9"],\n'
            '    ["CHAR", "_"],\n'
            '    ["BOOLEAN", "true"],\n'
            '    ["BOOLEAN", "false"]\n'
            "]\n\n"
            "Please generate a similar JSON grammar that focuses exclusively on the parameter above."
        )
    elif api_type == 'property' or api_type == 'properties':
        # Prompt for Property API (updated logic)
        # For Property APIs, we rely on 'Type' and 'API_Description' instead of explicit parameters.
        prompt = (
            f"Generate a context-free grammar in JSON format for the parameter '{param_name}' "
            f"of the following Property API. The grammar should follow these rules:\n"
            "1. Focus only on this single parameter.\n"
            "2. Provide a JSON array of rules to parse the parameter's type.\n"
            "3. Use the type information from the 'Type' field if available.\n\n"
            "API Information:\n"
            f"Object: {object_name}\n"
            f"API_Name: {api_name}\n"
            f"API_Type: {api_type}\n"
            f"API_Description: {api_description}\n"
            "Parameter Details:\n"
            f"{json.dumps({param_name: param_details}, indent=2)}\n\n"
            "Sample JSON Grammar (for reference):\n"
            "[\n"
            '    ["PARAM_VALUE", "[ {NUMBER}, {STRING}, {BOOLEAN} ]"],\n'
            '    ["NUMBER", "{INTEGER}"],\n'
            '    ["NUMBER", "{DECIMAL}"],\n'
            '    ["INTEGER", "{SIGN}{DIGIT_SEQUENCE}"],\n'
            '    ["DECIMAL", "{SIGN}{DIGIT_SEQUENCE}.{DIGIT_SEQUENCE}"],\n'
            '    ["SIGN", ""],\n'
            '    ["SIGN", "-"],\n'
            '    ["DIGIT_SEQUENCE", "{DIGIT}"],\n'
            '    ["DIGIT_SEQUENCE", "{DIGIT}{DIGIT_SEQUENCE}"],\n'
            '    ["DIGIT", "0"],\n'
            '    ["DIGIT", "1"],\n'
            '    ["DIGIT", "2"],\n'
            '    ["DIGIT", "3"],\n'
            '    ["DIGIT", "4"],\n'
            '    ["DIGIT", "5"],\n'
            '    ["DIGIT", "6"],\n'
            '    ["DIGIT", "7"],\n'
            '    ["DIGIT", "8"],\n'
            '    ["DIGIT", "9"],\n'
            '    ["STRING", "\"{FIELD_TYPE}\""],\n'
            '    ["FIELD_TYPE", "\"text\""],\n'
            '    ["FIELD_TYPE", "\"button\""],\n'
            '    ["FIELD_TYPE", "\"combobox\""],\n'
            '    ["FIELD_TYPE", "\"listbox\""],\n'
            '    ["FIELD_TYPE", "\"checkbox\""],\n'
            '    ["FIELD_TYPE", "\"radiobutton\""],\n'
            '    ["FIELD_TYPE", "\"signature\""]\n'
            '    ["STRING", "\"{FIELD_NAME}\""],\n'
            '    ["FIELD_NAME", "{NAME_PART}"],\n'
            '    ["FIELD_NAME", "{NAME_PART}.{FIELD_NAME}"],\n'
            '    ["NAME_PART", "{CHAR}{NAME_PART}"],\n'
            '    ["NAME_PART", "{CHAR}"],\n'
            '    ["CHAR", "a"],\n'
            '    ["CHAR", "b"],\n'
            '    ["CHAR", "c"],\n'
            '    ["CHAR", "d"],\n'
            '    ["CHAR", "e"],\n'
            '    ["CHAR", "f"],\n'
            '    ["CHAR", "g"],\n'
            '    ["CHAR", "h"],\n'
            '    ["CHAR", "i"],\n'
            '    ["CHAR", "j"],\n'
            '    ["CHAR", "k"],\n'
            '    ["CHAR", "l"],\n'
            '    ["CHAR", "m"],\n'
            '    ["CHAR", "n"],\n'
            '    ["CHAR", "o"],\n'
            '    ["CHAR", "p"],\n'
            '    ["CHAR", "q"],\n'
            '    ["CHAR", "r"],\n'
            '    ["CHAR", "s"],\n'
            '    ["CHAR", "t"],\n'
            '    ["CHAR", "u"],\n'
            '    ["CHAR", "v"],\n'
            '    ["CHAR", "w"],\n'
            '    ["CHAR", "x"],\n'
            '    ["CHAR", "y"],\n'
            '    ["CHAR", "z"],\n'
            '    ["CHAR", "A"],\n'
            '    ["CHAR", "B"],\n'
            '    ["CHAR", "C"],\n'
            '    ["CHAR", "D"],\n'
            '    ["CHAR", "E"],\n'
            '    ["CHAR", "F"],\n'
            '    ["CHAR", "G"],\n'
            '    ["CHAR", "H"],\n'
            '    ["CHAR", "I"],\n'
            '    ["CHAR", "J"],\n'
            '    ["CHAR", "K"],\n'
            '    ["CHAR", "L"],\n'
            '    ["CHAR", "M"],\n'
            '    ["CHAR", "N"],\n'
            '    ["CHAR", "O"],\n'
            '    ["CHAR", "P"],\n'
            '    ["CHAR", "Q"],\n'
            '    ["CHAR", "R"],\n'
            '    ["CHAR", "S"],\n'
            '    ["CHAR", "T"],\n'
            '    ["CHAR", "U"],\n'
            '    ["CHAR", "V"],\n'
            '    ["CHAR", "W"],\n'
            '    ["CHAR", "X"],\n'
            '    ["CHAR", "Y"],\n'
            '    ["CHAR", "Z"],\n'
            '    ["CHAR", "0"],\n'
            '    ["CHAR", "1"],\n'
            '    ["CHAR", "2"],\n'
            '    ["CHAR", "3"],\n'
            '    ["CHAR", "4"],\n'
            '    ["CHAR", "5"],\n'
            '    ["CHAR", "6"],\n'
            '    ["CHAR", "7"],\n'
            '    ["CHAR", "8"],\n'
            '    ["CHAR", "9"],\n'
            '    ["CHAR", "_"],\n'
            '    ["BOOLEAN", "true"],\n'
            '    ["BOOLEAN", "false"]\n'
            "]\n\n"
            "Please generate a similar JSON grammar for this single parameter."
        )
    else:
        logging.warning(
            f"Unknown API_Type '{api_type}' for API '{api_name}'. Skipping grammar generation."
        )
        return None

    try:
        logging.info(f"Prompt for param '{param_name}': {prompt}")
        # Call the OpenAI API with the constructed prompt
        assistant_reply = grammar_generation_agent.communicate(
            prompt,
            include_system_prompt = True,
            max_tokens=8192,
            temperature=0,
            stop=None
        ).strip()

        logging.info(f"Response from LLM for param '{param_name}': {assistant_reply}")

        # Initialize the JSON string to be parsed
        grammar_json_str = assistant_reply

        # Check if the reply is enclosed within a JSON code block
        if assistant_reply.startswith("```json") and assistant_reply.endswith("```"):
            grammar_json_str = assistant_reply[len("```json") : -len("```")].strip()
        else:
            # In case there are multiple code blocks or mixed content, search for the JSON code block
            start_idx = assistant_reply.find("```json")
            end_idx = assistant_reply.find("```", start_idx + 7)
            if start_idx != -1 and end_idx != -1:
                grammar_json_str = assistant_reply[start_idx + len("```json") : end_idx].strip()

        try:
            # Parse the JSON string into a Python object
            grammar = json.loads(grammar_json_str)
            return grammar
        except json.JSONDecodeError as json_err:
            print(f"JSON parsing error for param '{param_name}': {json_err}")
            print("Assistant's reply:")
            print(assistant_reply)
            logging.error(f"JSON parsing error for param '{param_name}': {json_err}")
            logging.error("Assistant's reply:")
            logging.error(assistant_reply)

            # try to query again to fix
            fix_prompt = (
                "The JSON you provided is invalid and cannot be parsed. "
                "Below is the parsing error and the JSON content. "
                "Please correct the JSON so that it is valid:\n\n"
                f"Error message:\n{json_err}\n\n"
                "Invalid JSON content:\n"
                "```\n"
                f"{grammar_json_str}\n"
                "```\n\n"
                "Please provide a corrected version of the JSON only (no additional explanations), "
                "and ensure it is valid."
            )

            logging.info(f"Fix prompt for invalid JSON of param '{param_name}': {fix_prompt}")
            assistant_reply_fix = grammar_generation_agent.communicate(
                fix_prompt,
                include_system_prompt=True,
                max_tokens=8192,
                temperature=0,
                stop=None
            ).strip()

            logging.info(f"Fix response from LLM for param '{param_name}': {assistant_reply_fix}")

            grammar_json_str_fixed = assistant_reply_fix
            if assistant_reply_fix.startswith("```json") and assistant_reply_fix.endswith("```"):
                grammar_json_str_fixed = assistant_reply_fix[len("```json") : -len("```")].strip()
            else:
                start_idx = assistant_reply_fix.find("```json")
                end_idx = assistant_reply_fix.find("```", start_idx + 7)
                if start_idx != -1 and end_idx != -1:
                    grammar_json_str_fixed = assistant_reply_fix[start_idx + len("```json") : end_idx].strip()

            # parse again
            try:
                grammar_fixed = json.loads(grammar_json_str_fixed)
                return grammar_fixed
            except json.JSONDecodeError as fix_err:
                logging.error(
                    f"Failed to parse the corrected JSON from LLM for param '{param_name}': {fix_err}"
                )
                logging.error("Assistant's fix reply:")
                logging.error(assistant_reply_fix)
                return None

    except Exception as e:
        # Log any errors that occur during the API call
        logging.error(
            f"Error generating grammar for param '{param_name}' of API '{api_name}': {e}"
        )
        return None
    

def generate_return_type(api_info: Dict[str, Any], return_type_hint_key: str) -> Optional[str]:
    object_name = api_info.get('Object', '')
    api_name = api_info.get('API_Name', '')
    api_type = api_info.get('API_Type', '').lower()
    api_description = api_info.get('API_Description', '')
    return_type_hint = api_info.get(return_type_hint_key, '')

    # Construct the user query prompt
    user_prompt = (
        "API Documentation Analysis Request:\n"
        "----------------------------------\n"
        f"Object: {object_name}\n"
        f"API Name: {api_name}\n"
        f"API Type: {api_type}\n"
        f"Description: {api_description}\n"
        f"Existing Type Hint: {return_type_hint if return_type_hint else 'None'}\n\n"
        "Required Response Format:\n"
        '{"Return_Type": "<type_specification>"}'
    )

    try:
        # Call the language model with system prompt and user query
        response = return_type_agent.communicate(
            user_prompt,
            include_system_prompt = True,
            max_tokens=8192,
            temperature=0,
            stop=None
        ).strip()

        logging.info(f"Response from LLM for API '{api_name}': {response}")

        # Handle code block wrapping
        json_str = response
        if json_str.startswith("```json") and json_str.endswith("```"):
            json_str = json_str[7:-3].strip()
        elif json_str.startswith("```") and json_str.endswith("```"):
            json_str = json_str[3:-3].strip()

        # Parse JSON response
        try:
            result = json.loads(json_str)
            if not isinstance(result, dict):
                raise ValueError("Response is not a JSON object")
            
            return_type = result.get("Return_Type")
            if not isinstance(return_type, str):
                raise ValueError("Return_Type is not a string")
            
            # Validate type format
            if re.match(r'^[\w\s<>\[\],\-]+$', return_type):
                return return_type
            logging.warning(f"Invalid type format: {return_type}")
            
        except (json.JSONDecodeError, ValueError) as e:
            logging.error(f"JSON parsing failed: {str(e)}")
            logging.debug(f"Original response: {response}")
            return None

    except Exception as e:
        logging.error(f"API query failed for {api_name}: {str(e)}")
        return None

    return None


def check_parameters_condition(api_info: Dict[str, Any], condition: str, result_key: str) -> Optional[Dict[str, List[str]]]:
    api_name = api_info.get('API_Name', '')
    prompt = (
        f"API Information:\n"
        f"API Name: {api_name}\n"
        f"API Type: {api_info.get('API_Type', '')}\n"
        f"API Description: {api_info.get('API_Description', '')}\n"
        f"Parameters: {json.dumps(api_info.get('Parameters'), indent=2)}\n\n"
        f"\nCondition to check:\n{condition}\n\n"
        "Please list ONLY the parameter names that satisfy this condition, formatted as a JSON array.\n"
        "If there are no parameters that meet the conditions, return an empty array without any explanation."
    )
    
    try:
        # Call the LLM with the constructed prompt
        response = parameter_condition_agent.communicate(
            prompt,
            max_tokens=8192,
            temperature=0,
            stop=None
        )

        logging.info(f"Response from LLM for API '{api_name}': {response}")
        
        # Extract JSON array from response
        json_str = response.strip()
        if json_str.startswith("```json"):
            json_str = json_str[json_str.find('['):json_str.rfind(']')+1]
        
        # Parse the response
        matched_params = json.loads(json_str)
        
        return {result_key: matched_params}
        
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse LLM response: {e}\nResponse content: {response}")
        return {result_key: []}
    except Exception as e:
        logging.error(f"Error during parameter condition check: {e}")
        return None
    

def check_grammar_exist(
    object_name: str,
    api_type: str,
    api_name: str,
    param_name: str,
    base_dir: str
) -> bool:
    try:
        # Determine the subdirectory based on api_type
        if api_type.lower() == 'method':
            sub_dir = 'methods'
        elif api_type.lower() in ['property', 'properties']:
            sub_dir = 'properties'
        else:
            logging.warning(
                f"Unknown API_Type '{api_type}' for parameter '{param_name}'. Cannot check existence."
            )
            return False

        # Construct the full directory path
        dir_path = os.path.join(base_dir, object_name, sub_dir, api_name, param_name)

        # Define the file path for the grammar JSON
        file_path = os.path.join(dir_path, "grammar.json")

        # Return True if the grammar JSON file exists, otherwise False
        return os.path.exists(file_path)

    except Exception as e:
        # Log any errors that occur during the existence check process
        logging.error(
            f"Error checking grammar existence for parameter '{param_name}': {e}"
        )
        return False



def save_grammar_for_parameter(
    grammar: Any,
    object_name: str,
    api_type: str,
    api_name: str,
    param_name: str,
    base_dir: str
):
    try:
        if api_type.lower() == 'method':
            sub_dir = 'methods'
        elif api_type.lower() in ['property', 'properties']:
            sub_dir = 'properties'
        else:
            logging.warning(
                f"Unknown API_Type '{api_type}' for parameter '{param_name}'. Skipping save."
            )
            return

        # Construct the full directory path
        # We create a subdirectory for each parameter
        dir_path = os.path.join(base_dir, object_name, sub_dir, api_name, param_name)
        os.makedirs(dir_path, exist_ok=True)

        # Define the file path for the grammar JSON
        file_path = os.path.join(dir_path, "grammar.json")

        # Write the grammar JSON to the file with proper formatting
        with open(file_path, 'w', encoding='utf-8') as json_file:
            json.dump(grammar, json_file, indent=4)

        logging.info(f"Grammar for parameter '{param_name}' saved to '{file_path}'.")

    except Exception as e:
        # Log any errors that occur during the file saving process
        logging.error(
            f"Error saving grammar for parameter '{param_name}': {e}"
        )


def check_api_info_exist(
    object_name: str,
    api_type: str,
    api_name: str,
    base_dir: str
) -> bool:
    try:
        # Determine the subdirectory based on api_type
        if api_type.lower() == 'method':
            sub_dir = 'methods'
        elif api_type.lower() in ['property', 'properties']:
            sub_dir = 'properties'
        else:
            logging.warning(
                f"Unknown API_Type '{api_type}' for API '{api_name}'. Cannot check existence."
            )
            return False

        # Construct the full directory path
        dir_path = os.path.join(base_dir, object_name, sub_dir, api_name)

        # Define the file path for the API info JSON file
        api_info_path = os.path.join(dir_path, "API_INFO.json")

        # Return True if the API info JSON file exists, otherwise False
        return os.path.exists(api_info_path)

    except Exception as e:
        # Log any errors that occur during the existence check process
        logging.error(f"Error checking API info existence for API '{api_name}': {e}")
        return False


def save_api_info(basic_info: dict, base_dir: str):
    try:
        # Extract API details from the basic_info dictionary
        object_name = basic_info.get("Object")
        api_type = basic_info.get("API_Type")
        api_name = basic_info.get("API_Name")

        # Determine the subdirectory based on API_Type
        if api_type.lower() == 'method':
            sub_dir = 'methods'
        elif api_type.lower() in ['property', 'properties']:
            sub_dir = 'properties'
        else:
            logging.warning(f"Unknown API_Type '{api_type}'. Skipping save.")
            return

        # Construct the full directory path
        # Create a subdirectory for each API
        dir_path = os.path.join(base_dir, object_name, sub_dir, api_name)
        os.makedirs(dir_path, exist_ok=True)

        # Define the file path for saving API info in JSON format
        api_info_path = os.path.join(dir_path, "API_INFO.json")
        
        # Save the basic_info dictionary as JSON
        with open(api_info_path, 'w', encoding='utf-8') as info_file:
            json.dump(basic_info, info_file, indent=4)

        logging.info(f"API info saved to '{api_info_path}'.")

    except Exception as e:
        # Log any errors that occur during the file saving process
        logging.error(f"Error saving API INFO for API '{api_name}': {e}")



def save_empty_file(object_name: str, api_type: str, api_name: str, base_dir: str):
    try:
        # Determine the subdirectory based on API_Type
        if api_type.lower() == 'method':
            sub_dir = 'methods'
        elif api_type.lower() in ['property', 'properties']:
            sub_dir = 'properties'
        else:
            logging.warning(
                f"Unknown API_Type '{api_type}' for API '{api_name}'. Skipping empty file creation."
            )
            return

        # Construct the full directory path: base_dir/object_name/sub_dir/api_name
        dir_path = os.path.join(base_dir, object_name, sub_dir, api_name)
        os.makedirs(dir_path, exist_ok=True)

        # Define the file path for the empty JSON
        file_path = os.path.join(dir_path, "empty.json")

        # Write "empty parameter" to the file
        with open(file_path, 'w', encoding='utf-8') as json_file:
            json_file.write("empty parameter")

        logging.info(f"Empty parameter file created at '{file_path}'.")

    except Exception as e:
        logging.error(f"Error creating empty parameter file for API '{api_name}': {e}")


def main(api_descriptions_path: str, output_base_dir: str, model_name: str):
    global grammar_generation_agent, return_type_agent, parameter_condition_agent
    try:
        # Determine appropriate handler based on model name
        if model_name in OpenAIHandler.SUPPORTED_MODELS:
            grammar_generation_agent = OpenAIHandler(model_name)
            return_type_agent = OpenAIHandler(model_name)
            parameter_condition_agent = OpenAIHandler(model_name)
        elif model_name in AnthropicHandler.SUPPORTED_MODELS:
            grammar_generation_agent = AnthropicHandler(model_name)
            return_type_agent = AnthropicHandler(model_name)
            parameter_condition_agent = AnthropicHandler(model_name)
        else:
            raise UnsupportedModelError(f"Unsupported model: {args.model}")
    except UnsupportedModelError as e:
        print(f"Model error: {str(e)}")
        exit(1)
    except ValueError as e:
        # Handle missing API key error from handler initialization
        print(f"Configuration error: {str(e)}")
        exit(1)
    except Exception as e:
        print(f"Initialization error: {str(e)}")
        exit(1)

    # load system prompts for agents
    system_generate_grammar_path = Path("prompts", "system_generate_grammar_param.txt").resolve()
    grammar_generation_agent.load_system_prompt_from_file(system_generate_grammar_path)
    system_return_type_path = Path("prompts", "system_return_type.txt").resolve()
    return_type_agent.load_system_prompt_from_file(system_return_type_path)
    system_parameter_condition_path = Path("prompts", "system_parameter_condition.txt").resolve()
    parameter_condition_agent.load_system_prompt_from_file(system_parameter_condition_path)

    # Load API descriptions from the specified path
    try:
        objects_dict = load_objects_description(api_descriptions_path)
        logging.info(f"Loaded API descriptions from '{api_descriptions_path}'.")
    except Exception as e:
        print(f"Failed to load API descriptions: {e}")
        return
    
    # List to store information about parameters whose grammar generation fails
    failed_parameters = []

    # Iterate over each object and its APIs
    for object_name, apis in objects_dict.items():
        for api_name, api_info in apis.items():
            api_type = api_info.get('API_Type', '').lower()
            if api_type == "methods":
                api_version = api_info.get('Version', '').lower()
            else:
                api_version = api_info.get('Version_Key', '').lower()
            if api_version == "deprecated":
                logging.info(f"{object_name}.{api_name} is deprecated, skip this api")
                continue
            api_basic_info = {
                "Object": object_name,
                "API_Name": api_name,
                "API_Type": api_type,
                "Return_Type": None,
                "Scripts_Arg": None,
                "Actions_Arg": None
            }
            logging.info(f"Processing {api_type} API '{api_name}' of object '{object_name}'.")
            print(f"Processing {api_type} API '{api_name}' of object '{object_name}'...")

            # record if api info generation fails
            api_info_infer_fail = False

            # If the API is of type 'property' or 'properties', handle differently
            if api_type in ['property', 'properties']:
                # Prioritize getting the type and description from the type of Parameters
                parameters = api_info.get('Parameters', {})
                type_param = parameters.get('type', {})

                property_type = type_param.get('type') if type_param else api_info.get('Type')
                description = type_param.get('description', api_info.get('API_Description', ''))

                if not property_type:
                    # If there's no 'Type' field, we cannot generate a grammar, save empty file
                    logging.warning(f"No 'Type' found for Property API '{api_name}'. Saving empty.")
                    print((f"No parameters found for API '{api_name}'. Saving empty."))
                    save_empty_file(object_name, api_info.get('API_Type', ''), api_name, output_base_dir)
                    save_api_info(api_basic_info, output_base_dir)
                    continue

                # Construct a pseudo-parameter for the property using 'Type' and 'API_Description'
                # so that generate_grammar_for_parameter can work.
                param_name = api_name
                param_details = {
                    "type": property_type,
                    "description": description
                }

                # Skip generation of the grammar file already exists
                if check_grammar_exist(
                        object_name,
                        api_info.get('API_Type', ''),
                        api_name,
                        param_name,
                        output_base_dir
                    ):
                        logging.info(f"  Parameter '{param_name}' already exists, skip...")
                        print(f"  Parameter '{param_name}' already exists, skip...")
                        
                else:
                    # Generate grammar for this single 'propertyValue'
                    grammar = generate_grammar_for_parameter(api_info, param_name, param_details)
                    if grammar is None:
                        # Record failure information when grammar generation fails for the property parameter
                        failed_parameters.append({
                            "object": object_name,
                            "api": api_name,
                            "parameter": param_name
                        })
                        logging.error(f"Failed to generate grammar for property '{api_name}'.")
                        continue

                    # Save the generated grammar
                    save_grammar_for_parameter(
                        grammar,
                        object_name,
                        api_info.get('API_Type', ''),
                        api_name,
                        param_name,
                        output_base_dir
                    )

                if check_api_info_exist(
                    object_name,
                    api_info.get('API_Type', ''),
                    api_name,
                    output_base_dir
                ):
                    logging.info("Skip generating return type")
                    print("Skip generating return type")
                    
                else:
                    logging.info("Generate return type")
                    # get return type of this api (if has)
                    return_type = generate_return_type(api_info, "Type")
                    if return_type != None:
                        api_basic_info['Return_Type'] = return_type
                    else:
                        api_info_infer_fail = True
                    # logging.info(f"{api_name} return type is {return_type}")

            else:
                # Otherwise, we assume it's a Method API or something else that uses 'Parameters'
                parameters = api_info.get('Parameters', {})
                if not parameters:
                    logging.warning(f"No parameters found for API '{api_name}'. Saving empty.")
                    print((f"No parameters found for API '{api_name}'. Saving empty."))
                    save_empty_file(object_name, api_info.get('API_Type', ''), api_name, output_base_dir)
                    save_api_info(api_basic_info, output_base_dir)
                    continue

                # For each parameter, generate and save grammar
                for param_name, param_details in parameters.items():
                    # Skip generation of the grammar file already exists
                    if check_grammar_exist(
                        object_name,
                        api_info.get('API_Type', ''),
                        api_name,
                        param_name,
                        output_base_dir
                    ):
                        logging.info(f"  Parameter '{param_name}' already exists, skip...")
                        print(f"  Parameter '{param_name}' already exists, skip...")
                        
                    else:
                        print(f"  Generating grammar for parameter '{param_name}'...")
                        grammar = generate_grammar_for_parameter(api_info, param_name, param_details)
                        if grammar is None:
                            # Record failure information when grammar generation fails for the parameter
                            failed_parameters.append({
                                "object": object_name,
                                "api": api_name,
                                "parameter": param_name
                            })
                            print(f"  Failed to generate grammar for parameter '{param_name}'.")
                            logging.error(f"Failed to generate grammar for parameter '{param_name}' in API '{api_name}'.")
                            continue

                        # Save the generated grammar to the appropriate directory
                        save_grammar_for_parameter(
                            grammar,
                            object_name,
                            api_info.get('API_Type', ''),
                            api_name,
                            param_name,
                            output_base_dir
                        )

                if check_api_info_exist(
                    object_name,
                    api_info.get('API_Type', ''),
                    api_name,
                    output_base_dir
                ):
                    logging.info("Skip generating parameter check and return type")
                    print("Skip generating parameter check and return type")
                
                else:
                    logging.info("Check scripts parameters")
                    # No need for this part, only get return type
                    # check if api has parameters satify special requirements
                    # result = check_parameters_condition(
                    #     api_info,
                    #     "Parameters contain scripts to execute",
                    #     "Scripts_Arg"
                    # )
                    # if result != None:
                    #     api_basic_info['Scripts_Arg'] = result['Scripts_Arg']
                    # else:
                    #     api_info_infer_fail = True
                    # logging.info(f"Scripts_Arg: {result['Scripts_Arg']}")

                    # logging.info("Check action parameters")
                    # result = check_parameters_condition(
                    #     api_info,
                    #     "Parameters contains name of the trigger point to which to attach the action",
                    #     "Actions_Arg"
                    # )
                    # if result != None:
                    #     api_basic_info['Actions_Arg'] = result['Actions_Arg']
                    # else:
                    #     api_info_infer_fail = True
                    # logging.info(f"Actions_Arg: {result['Actions_Arg']}")

                    logging.info("Generate return type")
                    # get return type of this api (if has)
                    return_type = generate_return_type(api_info, "Returns")
                    if return_type != None:
                        api_basic_info['Return_Type'] = return_type
                    else:
                        api_info_infer_fail = True
                    # logging.info(f"{api_name} return type is {return_type}")

            if check_api_info_exist(
                object_name,
                api_info.get('API_Type', ''),
                api_name,
                output_base_dir
            ):
                logging.info("Skip saving API INFO")
                print("Skip saving API INFO")
            
            else:
                if api_info_infer_fail:
                    logging.error("Skip saving API INFO because of failure in info generation")
                else:
                    save_api_info(
                        api_basic_info,
                        output_base_dir
                    )

    # After processing all APIs, save all failed parameter information to a file
    failures_file_path = os.path.join(output_base_dir, "failed_parameters.json")
    try:
        with open(failures_file_path, 'w', encoding='utf-8') as f:
            json.dump(failed_parameters, f, indent=4)
        logging.info(f"Failed parameters information saved to '{failures_file_path}'.")
    except Exception as e:
        logging.error(f"Failed to save failed parameters information: {e}")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Generate API documentation grammar.')
    parser.add_argument('-i', '--input', required=True, 
                        help='Path to API descriptions directory')
    parser.add_argument('-o', '--output', required=True,
                        help='Base directory for output files')
    parser.add_argument('-m', '--model', required=True,
                        help='Model name to use (e.g. gpt-4, claude-3-sonnet)')
    args = parser.parse_args()

    # Resolve input and output directories to absolute paths
    API_DESCRIPTIONS_PATH = Path(args.input).resolve()
    OUTPUT_BASE_DIR = Path(args.output).resolve()

    # Ensure output directory exists
    OUTPUT_BASE_DIR.mkdir(parents=True, exist_ok=True)

    # Run the main generation process
    main(API_DESCRIPTIONS_PATH, OUTPUT_BASE_DIR, args.model)
