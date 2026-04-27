import ast
import csv
import glob
import os
import yaml

def load_requirements(path):
    with open(path, "r", encoding="utf-8") as f:
        reqs = yaml.safe_load(f)
    return {r["id"]: r["text"] for r in reqs}

class ReqVisitor(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename = filename
        self.current_function = None
        self.req_mappings = [] # List of tuples: (req_id, test_case)

    def visit_FunctionDef(self, node):
        # Track which function we are currently inside
        old_func = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_func

    def visit_Assign(self, node):
        # Look for REQS = ["REQ-XXX"]
        for tgt in node.targets:
            if isinstance(tgt, ast.Name) and tgt.id == "REQS":
                if isinstance(node.value, ast.List):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            req_id = elt.value
                            # Format as filename::function_name
                            if self.current_function:
                                test_case = f"{self.filename}::{self.current_function}"
                            else:
                                test_case = f"{self.filename}::GLOBAL"
                            self.req_mappings.append((req_id, test_case))
        self.generic_visit(node)

def extract_reqs_from_test_file(path):
    with open(path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)

    filename = os.path.basename(path)
    visitor = ReqVisitor(filename)
    visitor.visit(tree)
    return visitor.req_mappings

def main():
    root = os.path.dirname(os.path.dirname(__file__))
    req_path = os.path.join(root, "requirements.yaml")
    tests_glob = os.path.join(root, "tests", "test_*.py")
    out_path = os.path.join(root, "traceability_matrix.csv")

    requirements = load_requirements(req_path)

    # Keep track of which requirements have tests mapped
    tested_reqs = set()
    rows = []

    # 1. Extract mapped requirements from test files
    for test_file in glob.glob(tests_glob):
        mappings = extract_reqs_from_test_file(test_file)
        for req_id, test_case in mappings:
            tested_reqs.add(req_id)
            rows.append({
                "requirement_id": req_id,
                "requirement_text": requirements.get(req_id, "UNKNOWN_REQUIREMENT_ID"),
                "test_case": test_case,
            })

    # 2. Find requirements that have NO tests
    for req_id, text in requirements.items():
        if req_id not in tested_reqs:
            rows.append({
                "requirement_id": req_id,
                "requirement_text": text,
                "test_case": "** NO TEST FOUND **", # Flag missing tests
            })

    # 3. Write output to CSV
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["requirement_id", "requirement_text", "test_case"])
        w.writeheader()
        # Sort by Requirement ID, then Test Case
        for r in sorted(rows, key=lambda x: (x["requirement_id"], x["test_case"])):
            w.writerow(r)

    print(f"Wrote {out_path}")
    print(f"Coverage: {len(tested_reqs)}/{len(requirements)} requirements tested.")

if __name__ == "__main__":
    main()
