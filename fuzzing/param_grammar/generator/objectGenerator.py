import os
import random
from typing import List
from .apiGenerator import MethodGenerator, PropertyGenerator

class ObjectGenerator:
    def __init__(self, folder_path: str, config: dict):
        self.folder_path = folder_path
        self.config = config  # Store the config for later use

        # A variable to store the object's name. You can customize how you determine the name.
        # Here, we simply take the folder name as the object's name.
        self.object_name = os.path.basename(os.path.normpath(folder_path))

        # An array to store the names of this object's instances.
        self.instances: List[str] = []
        self.permenent_instances: List[str] = []

        # Prepare valid and invalid API generator lists
        self.method_generators = {}
        self.property_generators = {}
        self.method_generators_invalid = {}
        self.property_generators_invalid = {}

        # Load method APIs
        methods_path = os.path.join(folder_path, "methods")
        if os.path.isdir(methods_path):
            self._load_apis(methods_path, MethodGenerator)
        
        # Load property APIs
        properties_path = os.path.join(folder_path, "properties")
        if os.path.isdir(properties_path):
            self._load_apis(properties_path, PropertyGenerator)

        self.api_list = self._get_api_list()

    def _load_apis(self, api_folder_path: str, generator_cls):
        blocklist = self.config.get("blocklist", [])
        
        for item in os.listdir(api_folder_path):
            item_path = os.path.join(api_folder_path, item)
            if os.path.isdir(item_path):
                try:
                    generator = generator_cls(item_path)
                    full_api_name = f"{self.object_name}.{generator.api_name}"
                    
                    # Create target list based on blocklist status and generator type
                    if full_api_name in blocklist:
                        target_dict = self.method_generators_invalid if generator_cls == MethodGenerator else self.property_generators_invalid
                    else:
                        target_dict = self.method_generators if generator_cls == MethodGenerator else self.property_generators
                    target_dict[generator.api_name] = generator
                    
                except (FileNotFoundError, ValueError) as e:
                    print(f"[X] Error in {item_path}, {e}")
                    pass

    def _get_api_list(self) -> List[str]:
        apis = []
        apis.extend(self.method_generators.keys())
        apis.extend(self.property_generators.keys())
        apis.extend(self.method_generators_invalid.keys())
        apis.extend(self.property_generators_invalid.keys())
        
        # Convert to list to ensure proper return type.
        return list(apis)

    def add_instance(self, instance_name: str):
        if instance_name not in self.instances:
            self.instances.append(instance_name)

    def add_permenent_instance(self, instance_name: str):
        if instance_name not in self.permenent_instances:
            self.permenent_instances.append(instance_name)
            self.instances.extend([instance_name] * 5)


    def remove_instance(self, instance_name: str):
        if instance_name in self.instances:
            self.instances.remove(instance_name)


    def clean_instance(self):
        self.instances = []
        for item in self.permenent_instances:
            self.instances.extend([item] * 5)

    
    def get_specific_api_call_statement(self, api_name: str) -> str:
        if not self.instances:
            # print(f"// No instances available for object {self.object_name}.")
            return None 

        # Choose a random instance
        instance_name = random.choice(self.instances)

        api_call_str = None
        # Check in valid method generators
        if api_name in self.method_generators:
            api_call_str = self.method_generators[api_name].generate_api_call_statement()
        # Check in valid property generators
        if api_name in self.property_generators:
            api_call_str = self.property_generators[api_name].generate_api_call_statement()
        # Check in invalid method generators
        if api_name in self.method_generators_invalid:
            api_call_str = self.method_generators_invalid[api_name].generate_api_call_statement()
        # Check in invalid property generators
        if api_name in self.property_generators_invalid:
            api_call_str = self.property_generators_invalid[api_name].generate_api_call_statement()
        
        if not api_call_str:
            return None
        
        # Prepend the instance name and a dot
        # return f"{instance_name}.{api_call_str}" 
        return f"try{{{instance_name}.{api_call_str}}} catch(e){{}}"
    
    
    def get_specific_api_call_raw(self, api_name: str) -> str:
        if not self.instances:
            # print(f"// No instances available for object {self.object_name}.")
            return None 

        # Choose a random instance
        instance_name = random.choice(self.instances)

        api_call_dict = None
        # Check in valid method generators
        if api_name in self.method_generators:
            api_call_dict = self.method_generators[api_name].generate_api_call_raw()
        # Check in valid property generators
        if api_name in self.property_generators:
            api_call_dict = self.property_generators[api_name].generate_api_call_raw()
        # Check in invalid method generators
        if api_name in self.method_generators_invalid:
            api_call_dict = self.method_generators_invalid[api_name].generate_api_call_raw()
        # Check in invalid property generators
        if api_name in self.property_generators_invalid:
            api_call_dict = self.property_generators_invalid[api_name].generate_api_call_raw()
        
        if not api_call_dict:
            return None
        
        api_call_dict['object_name'] = self.object_name
        api_call_dict['instance_name'] = instance_name

        # Prepend the instance name and a dot
        # return f"{instance_name}.{api_call_str}" 
        return api_call_dict

    def generate_api_call_statement(self) -> str:
        if not self.api_list:
            # print(f"// No APIs (methods/properties) available for this object {self.object_name}.")
            return None

        # Choose a random API
        api_name = random.choice(self.api_list)
        return self.get_specific_api_call_statement(api_name)
    
    
    def generate_api_call_raw(self) -> str:
        if not self.api_list:
            # print(f"// No APIs (methods/properties) available for this object {self.object_name}.")
            return None

        # Choose a random API
        api_name = random.choice(self.api_list)
        return self.get_specific_api_call_raw(api_name)
    
    
    def generate_all_valid_api_calls(self) -> List[str]:
        all_generators = list(self.method_generators.values()) + list(self.property_generators.values())
        call_statements = []

        if not self.instances:
            for _ in all_generators:
                call_statements.append("// No instances available for this object.")
            return call_statements

        for generator in all_generators:
            instance_name = random.choice(self.instances)
            api_call = generator.generate_api_call_statement()
            call_statement = f"try{{{instance_name}.{api_call}}} catch(e){{}}"
            call_statements.append(call_statement)

        return call_statements

    def generate_all_api_calls(self) -> List[str]:
        all_generators = list(self.method_generators.values()) + list(self.property_generators.values()) + list(self.method_generators_invalid.values()) + list(self.property_generators_invalid.values())
        call_statements = []

        if not self.instances:
            for _ in all_generators:
                call_statements.append("// No instances available for this object.")
            return call_statements

        for generator in all_generators:
            current_statements = []
            try:
                for _ in range(30):
                    instance_name = random.choice(self.instances)
                    api_call = generator.generate_api_call_statement()
                    call_statement = f"try{{{instance_name}.{api_call}}} catch(e){{}}"
                    current_statements.append(call_statement)
            except Exception as e:
                print(f"Error in generating API {generator.api_name}, {e}")
            call_statements.append("\n".join(current_statements))

        return call_statements
    
    def get_apis_with_no_parameters(self) -> List[str]:
        apis_no_params = []
        
        # Check all method generators
        for generator in self.method_generators:
            if generator._has_no_parameters:
                apis_no_params.append(generator.api_name)
        
        # Check all property generators
        for generator in self.property_generators:
            if generator._has_no_parameters:
                apis_no_params.append(generator.api_name)
        
        return apis_no_params