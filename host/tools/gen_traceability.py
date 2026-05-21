import ast
import csv
import glob
import os
import sys
import yaml

try:
    import doorstop
    DOORSTOP_AVAILABLE = True
except ImportError:
    DOORSTOP_AVAILABLE = False
    print("[Doorstop] 'doorstop' not installed. Run: pip install doorstop")



# Requirements loading


def load_requirements_yaml(path):
    """Load requirements from flat YAML file (legacy / fallback)."""
    with open(path, "r", encoding="utf-8") as f:
        reqs = yaml.safe_load(f)
    return {r["id"]: r["text"] for r in reqs}


def load_requirements_doorstop(root):
    """
    Load requirements from a Doorstop document tree rooted at `root`.
    Returns {req_id: text} or None if the tree cannot be found.
    The original REQ-XXX identifier is stored in each item's 'ref' field.
    """
    if not DOORSTOP_AVAILABLE:
        return None
    try:
        tree = doorstop.build(root=root)
        requirements = {}
        for document in tree.documents:
            for item in document.items:
                if not item.active:
                    continue
                req_id = (item.ref or "").strip() or str(item.uid)
                requirements[req_id] = item.text or ""
        if not requirements:
            return None
        print(f"[Doorstop] Loaded {len(requirements)} requirements from Doorstop tree.")
        return requirements
    except Exception as exc:
        print(f"[Doorstop] Could not load tree: {exc}")
        return None


def load_requirements(yaml_path, root=None):
    """
    Preferred source : Doorstop document tree (if available and initialised).
    Fallback source  : requirements.yaml.
    """
    if DOORSTOP_AVAILABLE and root:
        ds_reqs = load_requirements_doorstop(root)
        if ds_reqs:
            return ds_reqs
    print("[YAML] Loading requirements from requirements.yaml.")
    return load_requirements_yaml(yaml_path)


def init_doorstop_from_yaml(requirements, root):

    if not DOORSTOP_AVAILABLE:
        print("[Doorstop] Cannot initialise: 'doorstop' package not installed.")
        print("           Run:  pip install doorstop")
        return

    hlr_path = os.path.join(root, "requirements", "hlr")
    os.makedirs(hlr_path, exist_ok=True)

    tree = doorstop.build(root=root)

    try:
        doc = tree.find_document("HLR")
        print("[Doorstop] Found existing HLR document.")
    except doorstop.DoorstopError:
        # create_document(path, prefix) is the correct current API
        doc = tree.create_document(hlr_path, "HLR")
        print("[Doorstop] Created new HLR document.")

    # Index already-synced REQ IDs to avoid duplicates
    existing_refs = {
        (item.ref or "").strip()
        for item in doc.items
        if (item.ref or "").strip()
    }

    added = 0
    for req_id, text in requirements.items():
        if req_id in existing_refs:
            print(f"  ~ Skipping {req_id} (already exists)")
            continue
        item        = doc.add_item()
        item.ref    = req_id
        item.text   = text
        item.active = True
        item.save()
        added += 1
        print(f"  + Added {req_id}")

    print(f"\n[Doorstop] Synced {added} new item(s). "
          f"Total in document: {len(list(doc.items))}.")

    html_out = os.path.join(root, "requirements_doorstop.html")
    try:
        doorstop.publish(doc, html_out, ".html")
        print(f"[Doorstop] Published requirements report -> {html_out}")
    except Exception as exc:
        print(f"[Doorstop] HTML publish skipped: {exc}")



class ReqVisitor(ast.NodeVisitor):
    def __init__(self, filename):
        self.filename         = filename
        self.current_function = None
        self.req_mappings     = []

    def visit_FunctionDef(self, node):
        old_func              = self.current_function
        self.current_function = node.name
        self.generic_visit(node)
        self.current_function = old_func

    def visit_Assign(self, node):
        for tgt in node.targets:
            if isinstance(tgt, ast.Name) and tgt.id == "REQS":
                if isinstance(node.value, ast.List):
                    for elt in node.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            req_id    = elt.value
                            test_case = (
                                f"{self.filename}::{self.current_function}"
                                if self.current_function
                                else f"{self.filename}::GLOBAL"
                            )
                            self.req_mappings.append((req_id, test_case))
        self.generic_visit(node)


def extract_reqs_from_test_file(path):
    with open(path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=path)
    visitor = ReqVisitor(os.path.basename(path))
    visitor.visit(tree)
    return visitor.req_mappings


def main():
    init_mode = "--init-doorstop" in sys.argv

    root       = os.path.dirname(os.path.dirname(__file__))
    req_path   = os.path.join(root, "requirements.yaml")
    tests_glob = os.path.join(root, "tests", "test_*.py")
    out_path   = os.path.join(root, "traceability_matrix.csv")

    if init_mode:
        print("[Doorstop] Initialising Doorstop document from requirements.yaml...\n")
        yaml_reqs = load_requirements_yaml(req_path)
        init_doorstop_from_yaml(yaml_reqs, root)
        print("\n[Doorstop] Init complete.")
        print("           Re-run WITHOUT --init-doorstop to generate the matrix.")
        return

    requirements = load_requirements(req_path, root=root)

    tested_reqs = set()
    rows        = []

    for test_file in glob.glob(tests_glob):
        for req_id, test_case in extract_reqs_from_test_file(test_file):
            tested_reqs.add(req_id)
            rows.append({
                "requirement_id":   req_id,
                "requirement_text": requirements.get(req_id, "UNKNOWN_REQUIREMENT_ID"),
                "test_case":        test_case,
            })

    for req_id, text in requirements.items():
        if req_id not in tested_reqs:
            rows.append({
                "requirement_id":   req_id,
                "requirement_text": text,
                "test_case":        "** NO TEST FOUND **",
            })

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["requirement_id", "requirement_text", "test_case"]
        )
        writer.writeheader()
        for row in sorted(rows, key=lambda x: (x["requirement_id"], x["test_case"])):
            writer.writerow(row)

    print(f"Wrote {out_path}")
    print(f"Coverage: {len(tested_reqs)}/{len(requirements)} requirements tested.")


if __name__ == "__main__":
    main()
