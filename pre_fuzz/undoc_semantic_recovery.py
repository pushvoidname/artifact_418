import os
import json
from agentlib import OpenAIHandler, AnthropicHandler, UnsupportedModelError
from utils.util import *
import logging
from utils.Native_Object_Doc import Native_Object_Doc
from pathlib import Path
import argparse

logging.basicConfig(
    filename='openai_chat_semantic_recovery.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

semantic_recovery_agent = None


def construct_prompt(object_name, undoc_api, doc_object, undoc_object):
    prompt = f"Object Name: {object_name}\n"
    prompt += f"Undocumented API Name: {undoc_api['API_Name']}\n"
    prompt += f"API Type: {undoc_api.get('API_Type', 'Unknown')}\n"

    # Add parameters information
    parameters = undoc_api.get('Parameters', {})
    if parameters:
        prompt += "Parameters:\n"
        for param_name, param_type in parameters.items():
            prompt += f"  - {param_name} ({param_type})\n"
    else:
        prompt += "Parameters: None\n"

    # Add object description
    object_info = doc_object.get_info()
    object_description = object_info.get('apiDescription', 'No description available.')
    prompt += f"\nObject Description: {object_description}\n"

    # Add other APIs (methods and properties) of the object
    prompt += "\nOther Documented APIs:\n"
    methods = doc_object.get_methods()
    properties = doc_object.get_properties()

    for method_name in methods:
        prompt += f"  - Method: {method_name}\n"

    for prop_name in properties:
        prompt += f"  - Property: {prop_name}\n"

    prompt += "\nOther Undocumented APIs:\n"
    methods = undoc_object.get_methods()
    properties = undoc_object.get_properties()

    for method_name in methods:
        prompt += f"  - Method: {method_name}\n"

    for prop_name in properties:
        prompt += f"  - Property: {prop_name}\n"

    prompt += f"Based on the above information, provide a JSON object of {object_name}.{undoc_api['API_Name']} with the following structure. Ensure that only the JSON object is returned without any additional text.\n"

    # Instruction to generate JSON only
    prompt += """
{
  "Object": "Doc",
  "API_Name": "addField",
  "API_Type": "Method",
  "API_Description": "Creates a new form field and returns it as a Field object.",
  "API_Description_Reason": "Why you make this assumption for API_Description",
  "Returns": "The newly created Field object.",
  "Returns_Reason": "Why you make this assumption for Returns.",
  "Parameters": {
    "cName": {
      "description": "The name of the new field to create. This name can use the dot separator syntax to denote a hierarchy (for example, name.last creates a parent node, name, and a child node, last).",
      "description_reason": "Why you make this assumption for this parameter",
      "type": "string",
      "type_reason": "Why you make this assumption for this type"
    },
    "cFieldType": {
      "description": "The type of form field to create. Valid types are: text button combobox listbox checkbox radiobutton signature",
      "description_reason": "Why you make this assumption for this parameter",
      "type": "string",
      "type_reason": "Why you make this assumption for this type"
    },
    "nPageNum": {
      "description": "The 0-based index of the page to which to add the field.",
      "description_reason": "Why you make this assumption for this parameter",
      "type": "number",
      "type_reason": "Why you make this assumption for this type"
    },
    "oCoords": {
      "description": "An array of four numbers in rotated user space that specifies the size and placement of the form field. These four numbers are the coordinates of the bounding rectangle, in the following order: upper-left x, upper-left y, lower-right x and lower-right y. See also the Field object rect property. If you use the Info panel to obtain the coordinates of the bounding rectangle, you must transform them from info space to rotated user space. To do this, subtract the info space y coordinate from the on-screen page height.",
      "description_reason": "Why you make this assumption for this parameter",
      "type": "array",
      "type_reason": "Why you make this assumption for this type"
    }
  }
}
"""


    return prompt


def generate_description(prompt):
    """
    Call the OpenAI GPT-4o model to generate a JSON description based on the provided prompt.

    Args:
        prompt (str): The prompt to send to the GPT-4o model.

    Returns:
        dict: A dictionary containing the structured API documentation.
    """
    try:
        # Log the user prompt/input
        logging.info(f"User prompt: {prompt}")

        assistant_reply = semantic_recovery_agent.communicate(
            prompt,
            include_system_prompt = True,
            max_tokens=8192,
            temperature=0,
            stop=None
        ).strip()

        # Log the assistant's output
        logging.info(f"Assistant reply: {assistant_reply}")

        # Initialize the JSON string to be parsed
        json_str = assistant_reply

        # Check if the reply is enclosed within a JSON code block
        if assistant_reply.startswith("```json") and assistant_reply.endswith("```"):
            # Extract the JSON content between the code block delimiters
            json_str = assistant_reply[len("```json"): -len("```")].strip()
        else:
            # In case there are multiple code blocks or mixed content, search for the JSON code block
            start_idx = assistant_reply.find("```json")
            end_idx = assistant_reply.find("```", start_idx + 7)
            if start_idx != -1 and end_idx != -1:
                json_str = assistant_reply[start_idx + len("```json"): end_idx].strip()

        try:
            # Attempt to parse the assistant's reply as JSON
            api_description = json.loads(json_str)
            return api_description
        except json.JSONDecodeError as json_err:
            print(f"JSON parsing error: {json_err}")
            print("Assistant's reply:")
            print(assistant_reply)
            logging.error(f"JSON parsing error: {json_err}")
            logging.error("Assistant's reply:")
            logging.error(assistant_reply)
            return {"Description": "Failed to parse JSON from the assistant's response."}

    except Exception as e:
        print(f"Error when communicating with LLM: {e}")
        logging.error(f"Error when communicating with LLM: {e}")
        return {"Description": "Description generation failed due to an API error."}


def update_undocumented_apis(doc_objects, undoc_objects):
    undoc_objects_descriptions = {}
    fake_obj_path = Path("data") / "test" / "fake"
    fake_doc_object = Native_Object_Doc(fake_obj_path.resolve())

    for object_name, undoc_object in undoc_objects.items():
        undoc_objects_descriptions[object_name] = {}
        doc_object = doc_objects.get(object_name)
        if not doc_object:
            # print(f"Documented object for '{object_name}' not found. Skipping.")
            # continue
            doc_object = fake_doc_object

        # Process methods
        for api_name, undoc_api in undoc_object.get_methods().items():
            print(f"Generating description for undocumented method '{api_name}' in object '{object_name}'...")
            prompt = construct_prompt(object_name, undoc_api, doc_object, undoc_object)
            description = generate_description(prompt)
            undoc_objects_descriptions[object_name][api_name] = description
            # print(f"Description for '{api_name}':\n{description['Description']}\n")

        # Process properties
        for api_name, undoc_api in undoc_object.get_properties().items():
            print(f"Generating description for undocumented property '{api_name}' in object '{object_name}'...")
            prompt = construct_prompt(object_name, undoc_api, doc_object, undoc_object)
            description = generate_description(prompt)
            undoc_objects_descriptions[object_name][api_name] = description
            # print(f"Description for '{api_name}':\n{description['Description']}\n")

    return undoc_objects_descriptions


def save_updated_undoc_objects(undoc_objects_descriptions, base_path):
    for object_name, apis in undoc_objects_descriptions.items():
        # Define the path for the current object
        object_path = os.path.join(base_path, object_name)
        
        # Create the object directory if it doesn't exist
        os.makedirs(object_path, exist_ok=True)
        
        for api_name, api_data in apis.items():
            # Determine the subdirectory based on API_Type
            api_type = api_data.get("API_Type", "").lower()
            if api_type == "method":
                sub_dir = "methods"
            elif api_type == "property":
                sub_dir = "properties"
            else:
                # If API_Type is unknown or doesn't match expected types, default to a generic folder
                sub_dir = "others"
            
            # Define the path for the subdirectory
            sub_dir_path = os.path.join(object_path, sub_dir)
            
            # Create the subdirectory if it doesn't exist
            os.makedirs(sub_dir_path, exist_ok=True)
            
            # Define the file path for the API JSON file
            file_path = os.path.join(sub_dir_path, f"{api_name}.json")
            
            try:
                with open(file_path, 'w', encoding='utf-8') as file:
                    json.dump(api_data, file, indent=4, ensure_ascii=False)
                print(f"Updated {api_type} '{api_name}' in object '{object_name}'.")
            except IOError as e:
                print(f"Failed to save {api_type} '{api_name}' to '{file_path}': {e}")


def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Update undocumented API descriptions.")
    parser.add_argument("-d", "--documented", type=str, required=True,
                        help="Path to the documented API directory")
    parser.add_argument("-u", "--undocumented", type=str, required=True,
                        help="Path to the undocumented API directory")
    parser.add_argument("-o", "--output", type=str, required=True,
                        help="Path to save the updated undocumented API descriptions")
    parser.add_argument('-m', '--model', required=True,
                        help='Model name to use (e.g. gpt-4, claude-3-sonnet)')
    args = parser.parse_args()

    model_name = args.model
    global semantic_recovery_agent
    try:
        # Determine appropriate handler based on model name
        if model_name in OpenAIHandler.SUPPORTED_MODELS:
            semantic_recovery_agent = OpenAIHandler(model_name)
        elif model_name in AnthropicHandler.SUPPORTED_MODELS:
            semantic_recovery_agent = AnthropicHandler(model_name)
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
    semantic_recovery_path = Path("prompts", "system_semantic_recovery.txt").resolve()
    semantic_recovery_agent.load_system_prompt_from_file(semantic_recovery_path)

    # Define paths to documented and undocumented API directories and result directory
    documented_path = Path(args.documented) # Path("document_parser") / "json_all"
    undocumented_path = Path(args.undocumented) # Path("result") / "un_doc"
    result_path = Path(args.output) # Path("result") / "undoc_description"

    # Load documented and undocumented objects
    print("Loading documented objects...")
    doc_objects = load_doc_objects(documented_path.resolve())
    print(f"Loaded {len(doc_objects)} documented objects.\n")

    print("Loading undocumented objects...")
    undoc_objects = load_undoc_objects(undocumented_path.resolve())
    print(f"Loaded {len(undoc_objects)} undocumented objects.\n")

    # Generate descriptions for undocumented APIs
    print("Generating descriptions for undocumented APIs...")
    undoc_objects_descriptions = update_undocumented_apis(doc_objects, undoc_objects)

    # Save the updated undocumented APIs back to JSON files
    print("Saving updated undocumented APIs...")
    save_updated_undoc_objects(undoc_objects_descriptions, result_path.resolve())
    print("All updates completed.")


if __name__ == "__main__":
    main()
