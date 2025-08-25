import argparse
import json
import os
import mPDF
import monitor
import random
from param_grammar.generator import CodeGenerator, CodeGenerator_basic

TESTDIR = 'test'
TNUM = 30000  # Number of test files to generate
SNUM = 2048  # Number of API calls per test file

def getname(elem):
    """Extract numerical prefix from filename for sorting."""
    try:
        return int(elem.split(".")[0])
    except ValueError as e:
        print(f"Error parsing filename: {e}")
        return 0

class JSFuzz:
    def __init__(self, target, dry_run=False, weak_relation=False, symbolic_relation=False):
        # Create test directory if not exists
        if not os.path.exists(TESTDIR):
            os.makedirs(TESTDIR)
        self.ind = 0          # Current test index
        self.curfname = ''    # Current test filename
        self.dry_run = dry_run  # Dry run flag
        self.weak_relation = weak_relation
        self.symbolic_relation = symbolic_relation
        self.target = target # fuzzing target
  
    def _choose_target_monitor(self, file_name):
        if self.target == "adobe":
            return monitor.AdobeMonitor(file_name)
        elif self.target == "foxit":
            return monitor.FoxitMonitor(file_name)
        elif self.target == "xchange":
            return monitor.XchangeMonitor(file_name)
        else:
            print(f"[X] Unknown target {self.target} ...")
            return None

    def new_test(self):
        """Create new test case (to be implemented by subclasses)."""
        raise NotImplementedError("new_test method not implemented!")

    def run_testcase(self):
        """Execute and monitor the current test case."""
        monitor_instance = self._choose_target_monitor(self.curfname)
        monitor_instance.startUp()
        monitor_instance.writeResult()

    def startup(self):
        """Generate all test cases and optionally execute them."""
        for _ in range(TNUM):
            try:
                self.new_test()
                print(f"Generating: {self.curfname}")
                
                # Only execute test cases if not in dry-run mode
                if not self.dry_run:
                    self.run_testcase()
            except Exception as e:
                print(f"Error running test case: {e}")

    def runPDF(self):
        """Process all generated PDF test files."""
        if self.dry_run:
            return  # Skip processing in dry-run mode
        
        file_list = os.listdir(TESTDIR)
        file_list.sort(key=getname)
        for fname in file_list:
            monitor_instance = self._choose_target_monitor(fname)
            monitor_instance.startUp()
            monitor_instance.writeResult()


class Param_JSFuzz(JSFuzz):
    """Parameter-focused fuzzing implementation."""
    def __init__(self, base_directory, target, dry_run=False, weak_relation=False, symbolic_relation=False):
        super().__init__(target, dry_run, weak_relation, symbolic_relation)  # Initialize parent class
        # Load blocklist configuration
        blocklist_path = os.path.join('config', 'blocklist.txt')
        blocklist_apis = []
        
        if os.path.exists(blocklist_path):
            with open(blocklist_path, 'r') as bl_file:
                blocklist_apis = [line.strip() for line in bl_file if line.strip()]
        
        config = {'blocklist': blocklist_apis}

        # Load limitlist configuration
        limitlist_path = os.path.join('config', 'limitlist.txt')
        limitlist_apis = []
        
        if os.path.exists(limitlist_path):
            with open(limitlist_path, 'r') as bl_file:
                limitlist_apis = [line.strip() for line in bl_file if line.strip()]
        
        config['limitlist'] = limitlist_apis

        if weak_relation:
            weak_relation_path = os.path.join('config', 'all_relation.json')
            with open(weak_relation_path, 'r') as f:
                weak_relations = json.load(f)
            config['weak_relations'] = weak_relations

        if symbolic_relation:
            symbolic_relation_path = os.path.join('config', 'all_symbolic.json')
            with open(symbolic_relation_path, 'r') as f:
                symbolic_relations = json.load(f)
            config['symbolic_relations'] = symbolic_relations

        self.code_generator = CodeGenerator(base_directory, config)
        self.code_generator_basic = CodeGenerator_basic(base_directory, config)

    def new_test(self):
        """Generate new parameter test case."""
        if random.random() < 0.8:
            statements = self.code_generator.generate_api_statements_with_relation(SNUM, self.weak_relation, self.symbolic_relation)
            test_content = 'try{spell.available}catch(e){};\n' 
            test_content += '\n'.join(statements)
            test_content += '\ncloseDoc(1);\n'
            
            self.curfname = f'{self.ind}.pdf'
            output_path = os.path.join(TESTDIR, self.curfname)
            mPDF.make_pdf(test_content, output_path)
        else:
            statements = self.code_generator_basic.generate_api_statements_with_relation(SNUM, self.weak_relation, self.symbolic_relation)
            test_content = 'try{spell.available}catch(e){};\n' 
            test_content += '\n'.join(statements)
            test_content += '\ncloseDoc(1);\n'
            
            self.curfname = f'{self.ind}.pdf'
            output_path = os.path.join(TESTDIR, self.curfname)
            mPDF.make_pdf(test_content, output_path)
        self.ind += 1


if __name__ == '__main__':
    # Configure command line arguments
    parser = argparse.ArgumentParser(description='JavaScript Fuzzing Tool')
    parser.add_argument('-p', '--base_directory', required=True,
                      help='Base directory path for grammar files')
    parser.add_argument('-t', '--target', required=True,
                      help='Fuzz target: adobe, foxit, xchange')
    parser.add_argument('--dry', action='store_true',
                      help='Generate PDFs without executing tests')
    parser.add_argument('--relation', action='store_true',
                      help='Generate relevant APIs')
    parser.add_argument('--symbolic', action='store_true',
                      help='Using symbolic execution to assist generation')
    parser.add_argument('--run', action='store_true',
                      help='Run existing PDFs in test folder')
    
    args = parser.parse_args()
    
    fuzzer = Param_JSFuzz(args.base_directory, args.target, args.dry, args.relation, args.symbolic)
    
    if not args.run:
        # Execute fuzzing process
        fuzzer.startup()
    else:
        fuzzer.runPDF()