import os
import json
import random
import re

class ParameterGenerator:
    PLACEHOLDER_PATTERN = re.compile(r"\{([^{}]+)\}")

    def __init__(self, folder_path: str):
        """
        Initialize the ParameterGenerator by reading all JSON files in 'folder_path'
        and building the grammar dictionary.

        :param folder_path: Path to the folder containing one or more JSON grammar files.
        """
        self.folder_path = folder_path
        self.grammar = {}

        # New: Keep track of the default start symbol based on the first
        # non-terminal we encounter in the first JSON grammar file.
        self._default_start_symbol = None

        self._build_grammar()

    def _build_grammar(self):
        for filename in os.listdir(self.folder_path):
            full_path = os.path.join(self.folder_path, filename)
            # We only parse files with a .json extension
            if os.path.isfile(full_path) and filename.lower().endswith(".json"):
                self._parse_grammar_file(full_path)

    def _parse_grammar_file(self, json_file_path: str):

        with open(json_file_path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except Exception as e:
                print(f"[X] Error in {f}, {e}")

            for rule in data:
                if not isinstance(rule, list) or len(rule) != 2:
                    continue  # Skip invalid rules silently

                non_terminal, expansion = rule

                # If we haven't set the default start symbol yet, set it now
                if self._default_start_symbol is None:
                    self._default_start_symbol = non_terminal

                if non_terminal not in self.grammar:
                    self.grammar[non_terminal] = []
                self.grammar[non_terminal].append(expansion)

    def _expand_symbol(self, symbol: str, depth: int = 0, max_depth: int = 10) -> str:

        # If the symbol is not in the grammar dictionary, return it as a literal
        if symbol not in self.grammar:
            return symbol

        # If recursion depth exceeds max_depth, filter expansions that avoid further recursion
        possible_expansions = self.grammar[symbol]
        if depth >= max_depth:
            non_recursive = [exp for exp in possible_expansions if f"{{{symbol}}}" not in exp]
            if non_recursive:
                possible_expansions = non_recursive

        # Randomly pick an expansion
        expansion = random.choice(possible_expansions)

        # Find placeholders of the form {SOMETHING}
        placeholders = self.PLACEHOLDER_PATTERN.findall(expansion)

        # For each placeholder, recursively expand it and replace in the result
        result = expansion
        for ph in placeholders:
            expanded_ph = self._expand_symbol(ph, depth + 1, max_depth)
            result = result.replace(f"{{{ph}}}", expanded_ph, 1)

        # Restore literal braces
        result = result.replace("<<<LEFT_BRACE>>>", "{").replace("<<<RIGHT_BRACE>>>", "}")
        return result

    def generate_parameter(self, start_symbol: str = None) -> str:
        # If no start_symbol is provided or it's invalid, use the default start symbol
        if not start_symbol or start_symbol not in self.grammar:
            start_symbol = self._default_start_symbol

        # If the default start symbol is also None or missing, return empty string
        if not start_symbol or start_symbol not in self.grammar:
            return ""

        max_depth = random.randint(30, 50)
        return self._expand_symbol(start_symbol, 0, max_depth)
