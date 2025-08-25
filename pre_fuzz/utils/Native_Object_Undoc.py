import os
import json

class Native_Object_Undoc:
    """
    A class to load and store API information from methods and properties JSON files.

    Attributes:
        methods (dict): A dictionary containing method APIs with API_Name as keys.
        properties (dict): A dictionary containing property APIs with API_Name as keys.
    """

    def __init__(self, directory_path):
        """
        Initializes the Native_Object_Undoc instance by loading methods and properties from JSON files.

        Args:
            directory_path (str): The path to the directory containing 'methods' and 'properties' subdirectories.
        """
        self.methods = {}
        self.properties = {}
        self._load_api_data(directory_path)

    def _load_api_data(self, directory_path):
        """
        Loads API data from the specified directory's 'methods' and 'properties' subdirectories.

        Args:
            directory_path (str): The base directory path containing 'methods' and 'properties' folders.
        """
        # Define paths to the 'methods' and 'properties' subdirectories
        methods_dir = os.path.join(directory_path, 'methods')
        properties_dir = os.path.join(directory_path, 'properties')

        # Load methods APIs
        self.methods = self._load_json_files(methods_dir)

        # Load properties APIs
        self.properties = self._load_json_files(properties_dir)

    def _load_json_files(self, folder_path):
        """
        Loads JSON files from a specified folder and returns a dictionary with API_Name as keys.

        Args:
            folder_path (str): The path to the folder containing JSON files.

        Returns:
            dict: A dictionary mapping API_Name to its corresponding JSON content.
        """
        api_dict = {}
        if not os.path.isdir(folder_path):
            # If the folder does not exist, return an empty dictionary
            return api_dict

        # Iterate over all files in the folder
        for filename in os.listdir(folder_path):
            if filename.endswith('.json'):
                file_path = os.path.join(folder_path, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        api_name = data.get('API_Name')
                        if api_name:
                            api_dict[api_name] = data
                        else:
                            print(f"Warning: 'API_Name' not found in {file_path}. Skipping this file.")
                except (json.JSONDecodeError, IOError) as e:
                    print(f"Error reading {file_path}: {e}")
        return api_dict
    
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
        print("Usage: python Native_Object_Undoc.py <path_to_apis>")
        sys.exit(1)
    obj_path = sys.argv[1]
    # Example usage:
    # Assuming the directory structure is as follows:
    # /path/to/apis/
    # ├── methods/
    # │   ├── method1.json
    # │   └── method2.json
    # └── properties/
    #     ├── property1.json
    #     └── property2.json

    # Initialize the Native_Object_Undoc instance
    api_object = Native_Object_Undoc(obj_path)

    # Access methods and properties
    print(api_object.methods)
    print(api_object.properties)
