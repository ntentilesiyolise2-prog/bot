import ast
import random
import os
import shutil
from datetime import datetime
from utils.logger import setup_logger

logger = setup_logger(__name__)

class CodeMutator:
    def __init__(self, target_file="main.py"):
        self.target_file = target_file
        self.backup_dir = "backups"
        os.makedirs(self.backup_dir, exist_ok=True)

    def _backup(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"{self.backup_dir}/main_{timestamp}.py"
        shutil.copy2(self.target_file, backup_path)
        return backup_path

    def mutate(self):
        if not os.path.exists(self.target_file):
            logger.error("Target file not found.")
            return
        backup = self._backup()
        try:
            with open(self.target_file, 'r') as f:
                source = f.read()
            tree = ast.parse(source)

            # Simple mutation: find numeric constants and tweak them slightly
            class NumericMutator(ast.NodeTransformer):
                def visit_Constant(self, node):
                    if isinstance(node.value, (int, float)):
                        if random.random() < 0.1:
                            # Mutate by ±10%
                            factor = 1 + random.uniform(-0.1, 0.1)
                            node.value = node.value * factor
                            if isinstance(node.value, float):
                                node.value = round(node.value, 2)
                            elif isinstance(node.value, int):
                                node.value = int(node.value)
                    return node

            mutator = NumericMutator()
            new_tree = mutator.visit(tree)
            new_code = ast.unparse(new_tree)

            # Write mutated code to a temp file
            temp_file = f"{self.backup_dir}/main_mutated.py"
            with open(temp_file, 'w') as f:
                f.write(new_code)

            logger.info(f"Code mutated. Backup: {backup}, Mutated: {temp_file}")
            return temp_file
        except Exception as e:
            logger.error(f"Mutation failed: {e}")
            return None
