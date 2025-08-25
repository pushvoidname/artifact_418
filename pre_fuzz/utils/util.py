import os
from utils.Native_Object_Doc import Native_Object_Doc
from utils.Native_Object_Undoc import Native_Object_Undoc
import json
from typing import Dict, Any

def load_doc_objects(path):
    doc_objects = {}

    # Check if the provided path is a valid directory
    if not os.path.isdir(path):
        raise ValueError(f"The provided path '{path}' is not a valid directory.")

    # Iterate through each entry in the directory
    for entry in os.listdir(path):
        entry_path = os.path.join(path, entry)
        
        # Check if the entry is a directory
        if os.path.isdir(entry_path):
            try:
                # Instantiate Native_Object_Doc with the directory path
                doc_object = Native_Object_Doc(entry_path)
                
                # Add the object to the dictionary with the folder name as the key
                doc_objects[entry] = doc_object
            except Exception as e:
                # Handle exceptions related to object creation
                print(f"Failed to load object from '{entry_path}': {e}")

    return doc_objects


def load_undoc_objects(path):
    undoc_objects = {}

    # Check if the provided path is a valid directory
    if not os.path.isdir(path):
        raise ValueError(f"The provided path '{path}' is not a valid directory.")

    # Iterate through each entry in the directory
    for entry in os.listdir(path):
        entry_path = os.path.join(path, entry)
        
        # Check if the entry is a directory
        if os.path.isdir(entry_path):
            try:
                # Instantiate Native_Object_Doc with the directory path
                undoc_object = Native_Object_Undoc(entry_path)
                
                # Add the object to the dictionary with the folder name as the key
                undoc_objects[entry] = undoc_object
            except Exception as e:
                # Handle exceptions related to object creation
                print(f"Failed to load object from '{entry_path}': {e}")

    return undoc_objects


def load_objects_description_unknown(path):
    doc_objects = {}

    # Check if the provided path is a valid directory
    if not os.path.isdir(path):
        raise ValueError(f"The provided path '{path}' is not a valid directory.")

    # Iterate through each entry in the directory
    for entry in os.listdir(path):
        entry_path = os.path.join(path, entry)
        
        # Check if the entry is a directory
        if os.path.isdir(entry_path):
            try:
                # Instantiate Native_Object_Doc with the directory path
                doc_object = Native_Object_Doc(entry_path)
                
                # Add the object to the dictionary with the folder name as the key
                doc_objects[entry] = doc_object
            except Exception as e:
                # Handle exceptions related to object creation
                print(f"Failed to load object from '{entry_path}': {e}")

    return doc_objects


def load_objects_description(path: str) -> Dict[str, Dict[str, Any]]:
    # Initialize the main dictionary to store all objects and their APIs
    objects_dict: Dict[str, Dict[str, Any]] = {}

    # Check if the provided path exists and is a directory
    if not os.path.isdir(path):
        raise ValueError(f"The provided path '{path}' is not a valid directory.")

    # Iterate over each item in the main directory
    for object_name in os.listdir(path):
        object_path = os.path.join(path, object_name)
        
        # Proceed only if the item is a directory (i.e., an object folder)
        if os.path.isdir(object_path):
            # Initialize a dictionary to store APIs for the current object
            api_dict: Dict[str, Any] = {}

            # Define the potential subdirectories containing APIs
            for subfolder in ['methods', 'properties']:
                subfolder_path = os.path.join(object_path, subfolder)
                
                # Continue only if the subfolder exists and is a directory
                if os.path.isdir(subfolder_path):
                    # Iterate over each JSON file in the subfolder
                    for file_name in os.listdir(subfolder_path):
                        if file_name.endswith('.json'):
                            api_name = os.path.splitext(file_name)[0]
                            file_path = os.path.join(subfolder_path, file_name)
                            
                            # Read and parse the JSON file
                            try:
                                with open(file_path, 'r', encoding='utf-8') as json_file:
                                    api_info = json.load(json_file)
                                    api_dict[api_name] = api_info
                            except json.JSONDecodeError as e:
                                # Handle JSON parsing errors
                                print(f"Error decoding JSON in file '{file_path}': {e}")
                            except Exception as e:
                                # Handle other potential errors (e.g., file read issues)
                                print(f"Error reading file '{file_path}': {e}")

            # Add the object's API dictionary to the main dictionary
            objects_dict[object_name] = api_dict

    return objects_dict
