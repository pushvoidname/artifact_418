import os
import json
import random
from typing import Dict
from .parameterGenerator import ParameterGenerator
from .generator_utils import normalize_generated_value, generate_random_string, remove_special_characters, generate_printable_string


class APIGenerator:

    def __init__(self, folder_path: str):
        self.folder_path = folder_path
        self.param_generators: Dict[str, ParameterGenerator] = {}
        self._has_no_parameters = False

        # Load API information from API_INFO.json
        api_info_path = os.path.join(self.folder_path, "API_INFO.json")
        if not os.path.isfile(api_info_path):
            raise FileNotFoundError(f"API_INFO.json not found in the folder: {folder_path}")
        with open(api_info_path, "r", encoding="utf-8") as f:
            self.api_info = json.load(f)
        self.api_name = self.api_info.get("API_Name")
        self.return_type = self.api_info.get("Return_Type", None)
        if not self.api_name:
            raise ValueError("API_INFO.json must contain the 'API_Name' field.")

        self._discover_parameters()

    def _discover_parameters(self):
        items = os.listdir(self.folder_path)
        # Identify directories (treated as parameters)
        param_dirs = [
            item for item in items
            if os.path.isdir(os.path.join(self.folder_path, item))
        ]

        # If no subfolders exist, check for empty.json
        if not param_dirs:
            if "empty.json" in items:
                # Means this API call requires no parameters
                self._has_no_parameters = True
                return

        # Otherwise, build ParameterGenerator for each parameter directory
        for d in param_dirs:
            param_path = os.path.join(self.folder_path, d)
            self.param_generators[d] = ParameterGenerator(param_path)

    def generate_api_call(self) -> str:
        pass


class MethodGenerator(APIGenerator):
    def generate_api_call_statement(self) -> str:
        # If no parameters are needed, return the API call with an empty parameter dictionary.
        if self._has_no_parameters or not self.param_generators:
            return f"{self.api_name}({{}})"

        # Special case: If there is exactly one parameter and its key is "NoParameterName",
        # generate the API call by passing the value directly without a key.
        if len(self.param_generators) == 1 and "NoParameterName" in self.param_generators:
            # Retrieve the only ParameterGenerator.
            param_gen = self.param_generators["NoParameterName"]
            try:
                generated_value = param_gen.generate_parameter()
            except Exception as e:
                print(f"Error when generating {self.api_name}'s only param")
                generated_value = generate_random_string(3)
            normalized_value = normalize_generated_value(generated_value)
            # Return the API call with the parameter value passed directly.
            return f"{self.api_name}({normalized_value})"

        # Otherwise, generate each parameter's value using its ParameterGenerator,
        # and form key:value pairs for each.
        param_expressions = []
        for param_name, param_gen in self.param_generators.items():
            try:
                generated_value = param_gen.generate_parameter()
            except Exception as e:
                print(f"Error when generating {self.api_name}'s {param_name}")
                generated_value = generate_random_string(3)
            if random.random() < 0.1:
                if generated_value == "<<BUILTINOBJ>>" or generated_value == "<<SCRIPTS>>":
                    generated_value = generate_printable_string(8)
            normalized_value = normalize_generated_value(generated_value)
            param_expressions.append(f"{param_name}: {normalized_value}")

        # Join the parameter expressions with commas.
        joined_params = ", ".join(param_expressions)

        # Return the final API call string in key:value pair format inside curly braces.
        return f"{self.api_name}({{{joined_params}}})"
    

    def generate_api_call_raw(self) -> str:
        return_dict = {"api_name": self.api_name}
        return_dict["api_type"] = "method"
        return_dict["return_type"] = self.return_type
        return_dict["return_value"] = ""  
        if self.return_type and self.return_type not in ("unknown", "Boolean", "String", "Integer", "Number", "void"):
            normalize_return_type = remove_special_characters(self.return_type)
            return_dict["return_value"] = f"{normalize_return_type}_" + generate_random_string(5)
        # If no parameters are needed, return the API call with an empty parameter dictionary.
        if self._has_no_parameters or not self.param_generators:  
            return_dict['params'] = {}
            return return_dict

        # Special case: If there is exactly one parameter and its key is "NoParameterName",
        # generate the API call by passing the value directly without a key.
        if len(self.param_generators) == 1 and "NoParameterName" in self.param_generators:
            # Retrieve the only ParameterGenerator.
            param_gen = self.param_generators["NoParameterName"]
            try:
                generated_value = param_gen.generate_parameter()
            except Exception as e:
                print(f"Error when generating {self.api_name}'s only param")
                generated_value = generate_random_string(3)
            normalized_value = normalize_generated_value(generated_value)
            # Return the API call with the parameter value passed directly.
            return_dict['params'] = {"NoParameterName": normalized_value}
            return return_dict

        # Otherwise, generate each parameter's value using its ParameterGenerator,
        # and form key:value pairs for each.
        param_value = {}
        for param_name, param_gen in self.param_generators.items():
            try:
                generated_value = param_gen.generate_parameter()
            except Exception as e:
                print(f"Error when generating {self.api_name}'s {param_name}")
                generated_value = generate_random_string(3)
            if random.random() < 0.1:
                if generated_value == "<<BUILTINOBJ>>" or generated_value == "<<SCRIPTS>>":
                    generated_value = generate_printable_string(8)
            normalized_value = normalize_generated_value(generated_value)
            if param_name == "nPage" or param_name == "nPageNum":
                param_value[param_name] = str(random.randint(0, 9))
            else:
                param_value[param_name] = normalized_value

        return_dict['params'] = param_value

        # Return the final API call string in key:value pair format inside curly braces.
        return return_dict


class PropertyGenerator(APIGenerator):
    def generate_api_call_statement(self) -> str:
        # If the API is marked as having no parameters or no parameter generators exist,
        # return an API call with an empty value.
        if self._has_no_parameters or not self.param_generators:
            return f"{self.api_name}"

        # Ensure there is exactly one parameter generator.
        if len(self.param_generators) != 1:
            raise ValueError("PropertyGenerator must have exactly one parameter generator.")

        # Retrieve the single parameter generator.
        param_gen = next(iter(self.param_generators.values()))
        try:
            generated_value = param_gen.generate_parameter()
        except Exception as e:
            print(f"Error when generating {self.api_name}'s only param")
            generated_value = generate_random_string(3)
        normalized_value = normalize_generated_value(generated_value)
        # Generate and return the API call string in the format "API_Name = normalized_value".
        return f"{self.api_name} = {normalized_value}"

    def generate_api_call_raw(self) -> str:
        # If the API is marked as having no parameters or no parameter generators exist,
        # return an API call with an empty value.
        return_dict = {"api_name": self.api_name}
        return_dict["api_type"] = "property"
        return_dict["return_type"] = self.return_type
        return_dict["return_value"] = ""
        if self.return_type and self.return_type not in ("unknown", "Boolean", "String", "Integer"):
            normalize_return_type = remove_special_characters(self.return_type)
            return_dict["return_value"] = f"{normalize_return_type}_" + generate_random_string(5)
        if self._has_no_parameters or not self.param_generators:
            return_dict['params'] = {}
            return return_dict

        # Ensure there is exactly one parameter generator.
        if len(self.param_generators) != 1:
            raise ValueError("PropertyGenerator must have exactly one parameter generator.")

        # Retrieve the single parameter generator.
        param_gen = next(iter(self.param_generators.values()))
        try:
            generated_value = param_gen.generate_parameter()
        except Exception as e:
            print(f"Error when generating {self.api_name}'s only param")
            generated_value = generate_random_string(3)
        normalized_value = normalize_generated_value(generated_value)
        # Generate and return the API call string in the format "API_Name = normalized_value".
        return_dict['params'] = {self.api_name: normalized_value}
        return return_dict