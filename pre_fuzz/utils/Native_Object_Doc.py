import os
import json

class Native_Object_Doc:
    """
    A class to represent a native object with information, methods, and properties loaded from JSON files.
    """

    def __init__(self, directory_path):
        """
        Initializes the Native_Object_Doc by loading info, methods, and properties from the specified directory.

        Args:
            directory_path (str): The path to the directory containing object.json, methods, and properties folders.
        """
        self.info = {}
        self.methods = {}
        self.properties = {}

        # Load object.json into info
        object_json_path = os.path.join(directory_path, 'object.json')
        self._load_info(object_json_path)

        # Load methods from the methods directory
        methods_dir = os.path.join(directory_path, 'methods')
        self._load_api_data(methods_dir, self.methods)

        # Load properties from the properties directory
        properties_dir = os.path.join(directory_path, 'properties')
        self._load_api_data(properties_dir, self.properties)

    def _load_info(self, file_path):
        """
        Loads the object information from a JSON file.

        Args:
            file_path (str): The path to the object.json file.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                self.info = json.load(file)
            print(f"Loaded info from {file_path}")
        except FileNotFoundError:
            print(f"object.json not found at {file_path}. 'info' will be empty.")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {file_path}: {e}")

    def _load_api_data(self, directory, target_dict):
        """
        Loads API data from JSON files in a specified directory into a dictionary.

        Args:
            directory (str): The path to the directory containing JSON files.
            target_dict (dict): The dictionary to populate with API data.
        """
        if not os.path.isdir(directory):
            print(f"Directory {directory} does not exist. Skipping.")
            return

        for filename in os.listdir(directory):
            if filename.endswith('.json'):
                file_path = os.path.join(directory, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        api_data = json.load(file)
                        api_name = api_data.get('API_Name')
                        if api_name:
                            target_dict[api_name] = api_data
                            print(f"Loaded API '{api_name}' from {file_path}")
                        else:
                            print(f"'API_Name' not found in {file_path}. Skipping.")
                except json.JSONDecodeError as e:
                    print(f"Error decoding JSON from {file_path}: {e}")
                except Exception as e:
                    print(f"Unexpected error loading {file_path}: {e}")

    def get_info(self):
        """
        Returns the info dictionary.

        Returns:
            dict: The info data.
        """
        return self.info

    def get_methods(self):
        """
        Returns the methods dictionary.

        Returns:
            dict: The methods data.
        """
        return self.methods

    def get_properties(self):
        """
        Returns the properties dictionary.

        Returns:
            dict: The properties data.
        """
        return self.properties

import sys

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python Native_Object_Doc.py <path_to_apis>")
        sys.exit(1)
    obj_path = sys.argv[1]
    # Assume the directory structure is as follows:
    # /path/to/directory/
    # ├── object.json
    # ├── methods/
    # │   ├── method1.json
    # │   └── method2.json
    # └── properties/
    #     ├── property1.json
    #     └── property2.json

    # Initialize the Native_Object_Doc
    native_obj = Native_Object_Doc(obj_path)

    # Access the info, methods, and properties
    print(native_obj.get_info())
    print(native_obj.get_methods())
    print(native_obj.get_properties())
