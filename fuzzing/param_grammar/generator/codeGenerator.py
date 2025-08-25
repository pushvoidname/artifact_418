import os
import random
from typing import List, Dict
from .objectGenerator import ObjectGenerator
from .generator_utils import build_statement_from_raw_call, replace_statement_parameter, generate_statement_with_object_hook_simple, generate_statement_with_object_hook_complex, remove_braces
from .symbolic_execution_utils import solve_for_other_symbol
import copy
import json

object_instances: Dict[str, List[str]] = {
    "ADBC": ["this.ADBC"],
    "Annotation": [],
    "app": ["this.app", "app"],
    "bookmarkRoot": ["this.bookmarkRoot"],
    "Bookmark": ["this.bookmarkRoot.children[0]"],
    "Collab": ["this.Collab"],
    "color": ["this.color"],
    "constants": ["this.constants"],
    "cursor": ["this.cursor"],
    "Discovery": ["this.Net.Discovery"],
    "Doc": ["this", "this", "this"],
    "event": ["this.event"],
    "Field": [],
    "FormWorkflow": ["this.FormWorkflow"],
    "fs": ["this.app.fs", "app.fs"],
    "FX": ["this.FX"],
    "http": ["this.http"],
    "identity": ["this.identity"],
    "info": ["this.info"],
    "localFileStorage": ["this.FX.localFileStorage"],
    "localStorage": ["this.localStorage"],
    "media": ["this.media"],
    "methodProxy": ["this.methodProxy"],
    "Net": ["this.Net"],
    "page": ["this.page"],
    "persistentData": ["this.app.persistentData"],
    "ReadStream": ["this.ReadStream"],
    "RSS": ["this.RSS"],
    "search": ["this.search"],
    "security": ["this.security"],
    "shareIdentity": ["this.shareIdentity"],
    "SOAP": ["this.SOAP", "this.Net.SOAP"],
    "Span": [],
    "spell": ["this.spell", "spell"],
    "StreamDigest": ["this.StreamDigest"],
    "Subscriptions": ["this.Net.Subscriptions"],
    "Thermometer": ["this.app.thermometer"],
    "TTS": ["this.tts"],
    "util": ["this.util"],
    "viewState": ["this.viewState"]
}


class CodeGenerator:

    def __init__(self, folder_path: str, config: dict):
        self.folder_path = folder_path
        self.config = config  # Store the config for later use
        self.object_generators: Dict[str, ObjectGenerator] = {}
        self.permenent_object_list = set()
        self.tmp_object_list = set()
        self._init_object_generators()
        self.pre_sentences = self._get_instances_from_pdf()

    def _init_object_generators(self):
        for object_name, instances in object_instances.items():
            self.permenent_object_list.union(instances)
            subdir_path = os.path.join(self.folder_path, object_name)
            if not os.path.exists(subdir_path):
                print(f"[X] Can't find object {object_name}")
                continue
            # Create an ObjectGenerator and set its object_name， pass the config
            generator = ObjectGenerator(subdir_path, self.config)
            generator.object_name = object_name
            
            # Add all known instances for this object.
            for instance in instances:
                generator.add_permenent_instance(instance)
            
            # Store in dictionary with object name as key
            self.object_generators[object_name] = generator

    def _get_instances_from_pdf(self):
        code_statements = []
        rename_doc_statement = "try{var fthis = this;} catch(e){}"
        code_statements.append(rename_doc_statement)
        doc_generator = self.object_generators['Doc']
        doc_generator.add_permenent_instance("fthis")
        self.permenent_object_list.add("fthis")
        annot_generator = self.object_generators['Annotation']
        field_generator = self.object_generators['Field']
        for i in range(1, 11):
            get_field_statements = f"try{{var my_field{i} = this.getField(\"my_field{i}\");}} catch(e){{}}"
            get_annot_statements = f"try{{var my_annot{i} = this.getAnnot({i-1}, \"my_annot{i}\");}} catch(e){{}}"
            code_statements.append(get_annot_statements)
            code_statements.append(get_field_statements)
            annot_generator.add_permenent_instance(f"my_annot{i}")
            self.permenent_object_list.add(f"my_annot{i}")
            field_generator.add_permenent_instance(f"my_field{i}")
            self.permenent_object_list.add(f"my_field{i}")
            
        return code_statements


    def generate_api_statements(self, count: int) -> List[str]:
        statements = copy.deepcopy(self.pre_sentences)
        generate_count = 0
        while generate_count < count:
            # Randomly choose one of the available ObjectGenerators.
            chosen_generator = random.choice(list(self.object_generators.values()))
            # Generate an API call statement using the chosen ObjectGenerator.
            api_call = chosen_generator.generate_api_call_statement()
            if api_call == None:
                continue
            statements.append(api_call)
            generate_count += 1
        
        return statements
    

    def generate_api_statements_with_relation(self, count: int, weak_relation: bool, symbolic_relation: bool) -> List[str]:
        # clean all tmp instances
        for obj_name, obj_gen in self.object_generators.items():
            obj_gen.clean_instance()
        self.tmp_object_list = set()
        # If neither weak_relation nor symbolic_relation is set, just generate random statements.
        if not weak_relation and not symbolic_relation:
            return self.generate_api_statements(count)

        # statements = self._get_instances_from_pdf()
        statements = copy.deepcopy(self.pre_sentences)
        generated_count = 0

        blocklist = self.config["blocklist"]
        limitlist = self.config["limitlist"]

        # All possible <object>.<api> combinations for random fallback
        all_api_keys = []
        for obj_name, obj_gen in self.object_generators.items():
            for api_name in obj_gen.api_list:
                api_key = f"{obj_name}.{api_name}"
                if api_key in blocklist:
                    print(f"Find block API {api_key}")
                elif api_key in limitlist:
                    all_api_keys.append(api_key)
                    print(f"Find limit API {api_key}")
                else:
                    all_api_keys.extend([api_key] * 5)

        # Helper to pick a random API key from all possible ones
        def pick_random_api_key(api_list):
            pick_api = None
            while True:
                pick_api = random.choice(api_list) if api_list else None
                if pick_api in blocklist:
                    pick_api = random.choice(all_api_keys)
                    break
                elif pick_api in limitlist:
                    if random.random() < 0.8:
                        continue
                    else:
                        break
                else:
                    break

            return pick_api

        # Helper to parse "ObjectName.apiName" -> (object_name, api_name)
        def parse_api_key(api_key: str):
            parts = api_key.split('.')
            if len(parts) == 2:
                return parts[0], parts[1]
            return None, None
        
        def generate_hook_code() -> str:
            num_statements = random.randint(2, 8)
            hook_statements = []
            for _ in range(num_statements):
                api_key = pick_random_api_key(all_api_keys)
                obj_name, api_name = parse_api_key(api_key)
                if obj_name not in self.object_generators:
                    continue
                obj_gen = self.object_generators[obj_name]
                raw_call = obj_gen.get_specific_api_call_raw(api_name)
                if not raw_call:
                    continue
                # raw_call = replace_statement_parameter(raw_call, self.permenent_object_list | self.tmp_object_list)
                statement = build_statement_from_raw_call(raw_call)
                if statement:
                    hook_statements.append(statement)
            if not hook_statements:
                return ""
            
            hook_body = ' '.join([f'{stmt}' for stmt in hook_statements])
            return hook_body
        
        def generate_parameter_value_code() -> str:
            num_statements = random.randint(2, 8)
            hook_statements = []
            for _ in range(num_statements):
                api_key = pick_random_api_key(all_api_keys)
                obj_name, api_name = parse_api_key(api_key)
                if obj_name not in self.object_generators:
                    continue
                obj_gen = self.object_generators[obj_name]
                raw_call = obj_gen.get_specific_api_call_raw(api_name)
                if not raw_call:
                    continue
                # raw_call = replace_statement_parameter(raw_call, self.permenent_object_list | self.tmp_object_list)
                statement = build_statement_from_raw_call(raw_call)
                if statement:
                    hook_statements.append(statement)
            if not hook_statements:
                return ""
            
            hook_body = ' '.join([f'{stmt}' for stmt in hook_statements])
            hook_body = hook_body.replace('"', "'")
            # Wrap the hook_body with double quotes before returning
            hook_body = '"' + hook_body + '"'
            return hook_body
        
        def generate_loop_statement() -> str:
            loop_count = random.randint(1, 2)
            num_statements = random.randint(2, 5)
            loop_statements = []
            for _ in range(num_statements):
                api_key = pick_random_api_key(all_api_keys)
                obj_name, api_name = parse_api_key(api_key)
                if obj_name not in self.object_generators:
                    continue
                obj_gen = self.object_generators[obj_name]
                raw_call = obj_gen.get_specific_api_call_raw(api_name)
                if not raw_call:
                    continue
                # raw_call = replace_statement_parameter(raw_call, self.permenent_object_list | self.tmp_object_list)
                statement = build_statement_from_raw_call(raw_call)
                if statement:
                    loop_statements.append(statement)
            if not loop_statements:
                return ""
            loop_body = ' '.join([f'{stmt}' for stmt in loop_statements])
            return f"try{{for (var i = 0; i < {loop_count}; i++) {{{loop_body}}};}} catch(e){{}};"
        

        while generated_count < count:
            # print(f"{generated_count}/{count}")
            # 1) Generate a random API call (the "first" API call).x
            current_api_key = pick_random_api_key(all_api_keys)
            # Parse the fist API key
            first_obj_name, first_api_name = parse_api_key(current_api_key)
            if first_obj_name not in self.object_generators:
                continue
            first_obj_gen = self.object_generators[first_obj_name]
            first_raw_call = first_obj_gen.get_specific_api_call_raw(first_api_name)
            # If generation fails or returns None, try again
            if not first_raw_call:
                continue
            parameter_value_code = generate_parameter_value_code()
            first_raw_call = replace_statement_parameter(first_raw_call, self.permenent_object_list|self.tmp_object_list, parameter_value_code)
            
            # Convert raw call to a statement string
            first_statement = build_statement_from_raw_call(first_raw_call)
            if not first_statement:
                continue

            p = random.random()
            if p < 0.5:
                statements.append(first_statement)          
                generated_count += 1
                first_return_value = first_raw_call['return_value']
                if first_return_value != "":
                    self.tmp_object_list.add(first_return_value)
                    first_return_type = first_raw_call['return_type']
                    if first_return_type!= "Doc" and first_return_type in self.object_generators.keys():
                        generator = self.object_generators[first_return_type]
                        generator.add_instance(first_return_value)
                if generated_count >= count:
                    break
                continue
            elif p < 0.55:
                loop_statement = generate_loop_statement()
                statements.append(loop_statement)          
                generated_count += 1
                continue

            # 2) Decide whether we want to generate a "related" second call or a random one.
            second_api_key = None

            # Build the current API key from the first call
            current_api_key = f"{first_raw_call['object_name']}.{first_raw_call['api_name']}"
            # Attempt to pick a related API with 90% chance if weak_relation is True
            if weak_relation and random.random() < 0.9:
                related_candidates = self.config['weak_relations'].get(current_api_key, [])
                if related_candidates:
                    second_api_key = pick_random_api_key(related_candidates)
                    # in case we choose an API from blocklist
                    if second_api_key in blocklist:
                        second_api_key = None

            # If still no second_api_key chosen, pick from the entire pool
            if not second_api_key:
                second_api_key = pick_random_api_key(all_api_keys)
                if not second_api_key:
                    continue

            # Parse the second API key
            second_obj_name, second_api_name = parse_api_key(second_api_key)
            if second_obj_name not in self.object_generators:
                continue
            second_obj_gen = self.object_generators[second_obj_name]

            # 3) If symbolic_relation is True, with a 90% chance attempt a symbolic relation
            #    between the first and second API calls.
            second_raw_call = None
            if symbolic_relation and random.random() < 0.9:
                # Check if there's a symbolic relation entry for (api1 + api2) or (api2 + api1)
                comb1 = f"{current_api_key}+{second_api_key}"
                comb2 = f"{second_api_key}+{current_api_key}"
                symbolic_info = None
                if comb1 in self.config["symbolic_relations"]:
                    symbolic_info = self.config["symbolic_relations"][comb1]
                elif comb2 in self.config["symbolic_relations"]:
                    symbolic_info = self.config["symbolic_relations"][comb2]

                p = random.random()
                if p < 0.4:
                    hook_code = generate_hook_code()
                    os_name, obj_hook_code = generate_statement_with_object_hook_simple(first_raw_call, hook_code)
                    if os_name != None:
                        self.tmp_object_list.add(os_name)
                        # generate new statement after updating
                        first_statement = obj_hook_code+ ' ' + build_statement_from_raw_call(first_raw_call)
                elif p < 0.8:
                    hook_code = generate_hook_code()
                    os_name, obj_hook_code_with_api_call = generate_statement_with_object_hook_complex(first_raw_call, hook_code)
                    if os_name != None:
                        self.tmp_object_list.add(os_name)
                        # generate new statement after updating
                        first_statement = obj_hook_code_with_api_call

                # If we have symbolic_info (now a list) and constraints to process, attempt symbolic generation
                if symbolic_info:
                    # Generate raw second call
                    second_raw_call = second_obj_gen.get_specific_api_call_raw(second_api_name)
                    if not second_raw_call:
                        continue
                    parameter_value_code = generate_parameter_value_code()
                    second_raw_call = replace_statement_parameter(second_raw_call, self.permenent_object_list|self.tmp_object_list, parameter_value_code)
                    for info in symbolic_info:
                        # Skip if constraint is explicitly 'none'
                        constraint = info.get("constraint", "none")
                        
                        if constraint == "none":
                            continue

                        try:
                            known_param = info[current_api_key]
                            known_symbol = info[f"{current_api_key}.{known_param}"]
                            known_value = first_raw_call['params'][known_param]
                            solved_value = solve_for_other_symbol(info, known_symbol, known_value)
                            solved_value = remove_braces(solved_value)

                            #symbolic param override
                            second_raw_call['params'][info[second_api_key]] = solved_value
                        except Exception as e:
                            print(f"Error in symbolic solver: {e}")
                            pass

                    # Convert raw call to a statement string
                    second_statement = build_statement_from_raw_call(second_raw_call)
                    if not second_statement:
                        continue

                    # determine the API sequence
                    if symbolic_info[0].get("sequence", False):
                        # If 'sequence' is True, we assume the second API depends on the first
                        first_api_in_relation = symbolic_info[0]['api1']
                        if first_api_in_relation == current_api_key:
                            statements.append(first_statement)
                            statements.append(second_statement)
                        else:
                            statements.append(second_statement)
                            statements.append(first_statement)
                    # No sequence
                    else:
                        statements.append(first_statement)
                        statements.append(second_statement)
                        
                    
                    # Handle return values and object generation for both calls
                    for raw_call in [first_raw_call, second_raw_call]:
                        return_value = raw_call['return_value']
                        if return_value != "":
                            self.tmp_object_list.add(return_value)
                            return_type = raw_call['return_type']
                            if return_type!= "Doc" and return_type in self.object_generators.keys():
                                self.object_generators[return_type].add_instance(return_value)
                    
                    
                    generated_count += 2
                    if generated_count >= count:
                        break
                    
                else:
                    # Generate raw second call with the any parameters
                    second_raw_call = second_obj_gen.get_specific_api_call_raw(second_api_name)
                    if not second_raw_call:
                        continue
                    parameter_value_code = generate_parameter_value_code()
                    second_raw_call = replace_statement_parameter(second_raw_call, self.permenent_object_list|self.tmp_object_list, parameter_value_code)
                    second_statement = build_statement_from_raw_call(second_raw_call)
                    statements.append(first_statement)
                    statements.append(second_statement)

                    # Handle return values and object generation for both calls
                    for raw_call in [first_raw_call, second_raw_call]:
                        return_value = raw_call['return_value']
                        if return_value != "":
                            self.tmp_object_list.add(return_value)
                            return_type = raw_call['return_type']
                            if return_type != "Doc" and return_type in self.object_generators.keys():
                                self.object_generators[return_type].add_instance(return_value)
                        
                    generated_count += 2
                    if generated_count >= count:
                        break

            else:
                # Generate raw second call with the any parameters
                second_raw_call = second_obj_gen.get_specific_api_call_raw(second_api_name)
                if not second_raw_call:
                    continue
                parameter_value_code = generate_parameter_value_code()
                second_raw_call = replace_statement_parameter(second_raw_call, self.permenent_object_list|self.tmp_object_list, parameter_value_code)
                second_statement = build_statement_from_raw_call(second_raw_call)
                statements.append(first_statement)
                statements.append(second_statement)

                # Handle return values and object generation for both calls
                for raw_call in [first_raw_call, second_raw_call]:
                    return_value = raw_call['return_value']
                    if return_value != "":
                        self.tmp_object_list.add(return_value)
                        return_type = raw_call['return_type']
                        if return_type != "Doc" and return_type in self.object_generators.keys():
                            self.object_generators[return_type].add_instance(return_value)
                    
                generated_count += 2
                if generated_count >= count:
                    break
        
        return statements

    
    def generate_all_valid_api_statements(self) -> List[str]:
        all_statements = []
        for object_gen in self.object_generators.values():
            # Extend the list with the API call statements generated by this object.
            all_statements.extend(object_gen.generate_all_valid_api_calls())
        return all_statements

    def generate_all_api_statements(self) -> List[str]:
        all_statements = []
        for object_gen in self.object_generators.values():
            # Extend the list with the API call statements generated by this object.
            all_statements.extend(object_gen.generate_all_api_calls())
        return all_statements
