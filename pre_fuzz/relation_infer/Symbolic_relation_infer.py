import argparse
import os
import json
from openai import OpenAI
import logging
from pathlib import Path
from agentlib.agentHandler import OpenAIHandler, AnthropicHandler, UnsupportedModelError


# Configure logger
logging.basicConfig(
    filename='openai_chat_symbolic_relation.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

symbolic_relation_agent = None


def load_system_prompt(file_path: str) -> str:
    """Load system prompt from text file"""
    with open(file_path, 'r') as f:
        return f.read()
    

def process_directory(directory_path, result_dict):
    for object_name in os.listdir(directory_path):
        object_dir = os.path.join(directory_path, object_name)
        if not os.path.isdir(object_dir):
            continue
        
        for category in ['methods', 'properties']:
            category_dir = os.path.join(object_dir, category)
            if not os.path.exists(category_dir):
                continue
            
            for filename in os.listdir(category_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(category_dir, filename)
                    api_name = os.path.splitext(filename)[0]
                    dict_key = f"{object_name}.{api_name}"
                    with open(file_path, 'r') as json_file:
                        if category == 'methods':
                            result_dict[dict_key] = json.load(json_file)
                        else:
                            tmp_dict = json.load(json_file)
                            parameters = tmp_dict.get('Parameters', {})
                            type_param = parameters.get('type', {})

                            property_type = type_param.get('type') if type_param else tmp_dict.get('Type')
                            description = type_param.get('description', tmp_dict.get('API_Description', ''))
                            tmp_dict["Returns"] = property_type
                            tmp_dict["Parameters"] = {tmp_dict["API_Name"]: description}
                            result_dict[dict_key] = tmp_dict


def query_llm(api1_info, api2_info):
    # Construct the prompt for the model
    user_prompt = f"""Analyze the relationship between these two APIs:
    API 1: {json.dumps(api1_info)}
    API 2: {json.dumps(api2_info)}
    Provide response in specified JSON format."""
    
    # system_prompt = load_system_prompt(Path("prompts") / "system_Symbolic_relation_infer.txt")

    try:
        logging.info(f"Prompt: {user_prompt}")

        assistant_reply = symbolic_relation_agent.communicate(
            user_prompt,
            include_system_prompt = True,
            max_tokens=8192,
            temperature=0,
            stop=None
        ).strip()

        logging.info(f"Response from OpenAI: {assistant_reply}")

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
    
        return json.loads(grammar_json_str)
    except json.JSONDecodeError as json_err:
        # try to query again to fix
        print(f"JSON parsing error: {json_err}")
        print("Assistant's reply:")
        print(assistant_reply)
        logging.error(f"JSON parsing error: {json_err}")
        logging.error("Assistant's reply:")
        logging.error(assistant_reply)

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
        logging.info(f"Fix prompt for invalid JSON: {fix_prompt}")
        assistant_reply_fix = symbolic_relation_agent.communicate(
            fix_prompt,
            include_system_prompt=True,
            max_tokens=8192,
            temperature=0,
            stop=None
        ).strip()

        grammar_json_str = assistant_reply_fix

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
            return_value = json.loads(grammar_json_str)
            return return_value
        except json.JSONDecodeError as fix_err:
            logging.error(
                f"Failed to parse the corrected JSON from LLM: {fix_err}"
            )
            logging.error("Assistant's fix reply:")
            logging.error(assistant_reply_fix)
            return {"constraint": "error"}
    except Exception as e:
        logging.error(f"Error when processing: {str(e)}")
        print(f"Error when processing: {str(e)}")
        return {"constraint": "error"}


def process_relationships(relation_file, api_collection, output_dict):
    with open(relation_file, 'r') as f:
        relationships = json.load(f)

    failed_results = {}
    
    for api_name, related_apis in relationships.items():
        if api_name not in api_collection:
            logging.warning(f"Skip unknown api {api_name}")
            print(f"Skip unknown api {related_api}")
            continue
            
        for related_api in related_apis:
            # Check if both APIs exist in collection
            if related_api not in api_collection:
                logging.warning(f"Skip unknown api {related_api}")
                print(f"Skip unknown api {related_api}")
                continue

            if api_name == related_api:
                continue
                
            # Check if relationship already processed
            key1 = f"{api_name}+{related_api}"
            key2 = f"{related_api}+{api_name}"
            if key1 in output_dict or key2 in output_dict:
                logging.info(f"Skip existed relation inference for {api_name} and {related_api}")
                print(f"Skip existed relation inference for {api_name} and {related_api}")
                continue
                
            # Query GPT-4o model
            print(f"Infer relation between {api_name} and {related_api}")
            master_api_info = api_collection[api_name]
            related_api_info = api_collection[related_api]
            result = query_llm(master_api_info, related_api_info)
            
            # Initialize output list and results
            output_list = []
            results = result if isinstance(result, list) else [result]
            failed_flag = False

            for res in results:
                try:
                    # Validate result structure
                    api1 = res.get("api1", "")
                    api2 = res.get("api2", "")
                    constraint = res.get("constraint", "none")

                    if constraint == "none":
                        logging.info(f"Skip unrelated api {api1} and {api2}")
                        print(f"Skip unrelated api {api1} and {api2}")
                        failed_flag = True
                        break
                    
                    # Check API name consistency
                    if api1 not in (api_name, related_api) or api2 not in (api_name, related_api):
                        logging.error(f"Unknown API found: {api1}, {api2}, should be {api_name}, {related_api}")
                        print(f"Unknown API found: {api1}, {api2}, should be {api_name}, {related_api}")
                        raise ValueError("API name mismatch")
                        
                    # Validate parameters
                    arg1 = res.get("arg1", "")
                    arg2 = res.get("arg2", "")
                    if (arg1 not in api_collection[api1]["Parameters"].keys() or 
                        arg2 not in api_collection[api2]["Parameters"].keys()):
                        logging.error(f"Unknown parameter: {api1} missing {arg1} or {api2} missing {arg2}")
                        print(f"Unknown parameter: {api1} missing {arg1} or {api2} missing {arg2}")
                        raise ValueError("Invalid parameter")
                        
                    # Validate symbol entries
                    symbol1 = res.get("symbol1", "")
                    symbol2 = res.get("symbol2", "")
                    if not isinstance(symbol1, str) or not isinstance(symbol2, str):
                        raise TypeError("Symbol values must be strings")
                        
                    # Validate sequence type
                    sequence = res.get("sequence", False)
                    if not isinstance(sequence, bool):
                        raise TypeError("Sequence value must be boolean")

                    # Build result entry
                    output_list.append({
                        "api1": api1,
                        "api2": api2,
                        api_name: arg1,
                        related_api: arg2,
                        f"{api1}.{arg1}": symbol1,
                        f"{api2}.{arg2}": symbol2,
                        "sequence": sequence,
                        "type": res.get("type", ""),
                        "constraint": constraint
                    })

                except (KeyError, ValueError, TypeError) as e:
                    # Handle structural errors in GPT response
                    error_msg = f"Error processing {api_name}-{related_api}: {str(e)}"
                    logging.error(error_msg)
                    print(error_msg)
                    
                    # Add to failed results
                    failed_results.setdefault(api_name, []).append(related_api)
                    failed_flag = True
                    break

            if not failed_flag:
                output_dict[key1] = output_list

    return failed_results

def main():
    # Set up command line arguments
    parser = argparse.ArgumentParser(description='API relationship analyzer with GPT-4o validation')
    parser.add_argument('-d', required=True, help='Documented API directory')
    parser.add_argument('-u', required=True, help='Undocumented API directory')
    parser.add_argument('-r', required=True, help='Initial API relationships JSON file')
    parser.add_argument('-o', required=True, help='Output JSON file')
    parser.add_argument('-m', '--model', required=True, help='Model name to use (e.g. gpt-4, claude-3-sonnet)')
    args = parser.parse_args()

    model_name = args.model
    global symbolic_relation_agent
    try:
        # Determine appropriate handler based on model name
        if model_name in OpenAIHandler.SUPPORTED_MODELS:
            symbolic_relation_agent = OpenAIHandler(model_name)
        elif model_name in AnthropicHandler.SUPPORTED_MODELS:
            symbolic_relation_agent = AnthropicHandler(model_name)
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
    symbolic_relation_path = Path("prompts", "system_Symbolic_relation_infer.txt").resolve()
    symbolic_relation_agent.load_system_prompt_from_file(symbolic_relation_path)


    # Initialize data structures
    api_collection = {}
    relationships = {}

    # Process API documentation
    process_directory(args.d, api_collection)
    process_directory(args.u, api_collection)

    # Process relationships
    failed_results = process_relationships(args.r, api_collection, relationships)
    # Save results
    print("Saving failed results...")
    with open("failed_symbolic_results.json", 'w') as f:
        json.dump(failed_results, f, indent=2)


    # Output results
    logging.info(f"Total APIs collected: {len(api_collection)}")
    logging.info(f"Total relationships analyzed: {len(relationships)}")
    print(f"Total APIs collected: {len(api_collection)}")
    print(f"Total relationships analyzed: {len(relationships)}")
    # Save results
    print("Saving results...")
    with open(args.o, 'w') as f:
        json.dump(relationships, f, indent=2)
    # if relationships:
    #     sample_key = next(iter(relationships))
    #     print(f"Sample relationship ({sample_key}): {json.dumps(relationships[sample_key], indent=2)}")

if __name__ == '__main__':
    main()