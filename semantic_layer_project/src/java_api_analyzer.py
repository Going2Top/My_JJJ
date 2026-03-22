# -*- coding: utf-8 -*-
"""
Java API Analyzer - Extract API information from Java Controller files
"""
import re
from pathlib import Path
from typing import List, Dict, Any


class JavaAPIAnalyzer:
    """Java API Analyzer"""

    def __init__(self, controller_file: str):
        self.controller_file = Path(controller_file)
        self.content = self.controller_file.read_text(encoding='utf-8')

    def analyze(self) -> Dict[str, Any]:
        """Analyze Java controller file"""
        # Extract class info
        class_info = self._extract_class_info()

        # Extract APIs
        apis = self._extract_apis()

        return {
            'controller': class_info,
            'apis': apis,
            'file_path': str(self.controller_file)
        }

    def _extract_class_info(self) -> Dict[str, str]:
        """Extract class information"""
        # Extract class name
        class_match = re.search(r'public\s+class\s+(\w+)', self.content)
        class_name = class_match.group(1) if class_match else 'Unknown'

        # Extract class comment
        class_comment_match = re.search(r'/\*\*\s*\n\s*\*\s*([^\n]+)', self.content)
        class_comment = class_comment_match.group(1).strip() if class_comment_match else ''

        # Extract package
        package_match = re.search(r'package\s+([\w.]+);', self.content)
        package = package_match.group(1) if package_match else ''

        return {
            'name': class_name,
            'comment': class_comment,
            'package': package
        }

    def _extract_apis(self) -> List[Dict[str, Any]]:
        """Extract API methods"""
        apis = []

        # Find all methods with @GetMapping or @PostMapping
        method_pattern = r'/\*\*\s*\n\s*\*\s*([^\n]+).*?\*/\s*(?:@\w+.*?\n)*\s*@(GetMapping|PostMapping)\("([^"]+)"\)\s*public\s+Result<[^>]+>\s+(\w+)\(([^)]*)\)'

        for match in re.finditer(method_pattern, self.content, re.DOTALL):
            comment = match.group(1).strip()
            http_method = match.group(2)
            url = match.group(3)
            method_name = match.group(4)
            params = match.group(5)

            # Extract annotations
            method_start = match.start()
            method_text = self.content[max(0, method_start-500):match.end()]

            annotations = self._extract_annotations(method_text)

            # Parse parameters
            param_list = self._parse_parameters(params)

            apis.append({
                'comment': comment,
                'http_method': 'GET' if http_method == 'GetMapping' else 'POST',
                'url': url,
                'method_name': method_name,
                'parameters': param_list,
                'annotations': annotations
            })

        return apis

    def _extract_annotations(self, method_text: str) -> List[str]:
        """Extract method annotations"""
        annotations = []
        annotation_pattern = r'@(\w+)(?:\([^)]*\))?'

        for match in re.finditer(annotation_pattern, method_text):
            annotation = match.group(1)
            if annotation not in ['GetMapping', 'PostMapping']:
                annotations.append(annotation)

        return annotations

    def _parse_parameters(self, params_str: str) -> List[Dict[str, str]]:
        """Parse method parameters"""
        if not params_str.strip():
            return []

        params = []
        # Simple parameter parsing
        for param in params_str.split(','):
            param = param.strip()
            if param:
                # Extract type and name
                parts = param.split()
                if len(parts) >= 2:
                    param_type = parts[-2]
                    param_name = parts[-1]
                    params.append({
                        'type': param_type,
                        'name': param_name
                    })

        return params


def generate_api_semantic_layer(api_info: Dict[str, Any], controller_info: Dict[str, str], file_path: str) -> str:
    """Generate semantic layer document for a single API"""

    api = api_info
    controller = controller_info

    # Determine business domain
    if 'order' in file_path.lower():
        domain = 'Order Management'
    elif 'ticket' in file_path.lower():
        domain = 'Ticket Management'
    elif 'user' in file_path.lower():
        domain = 'User Management'
    elif 'pay' in file_path.lower():
        domain = 'Payment Management'
    elif 'passenger' in file_path.lower():
        domain = 'Passenger Management'
    else:
        domain = 'Unknown'

    # Determine semantic role
    if api['http_method'] == 'GET' and 'query' in api['url']:
        semantic_role = 'Query API'
    elif api['http_method'] == 'POST' and 'create' in api['url']:
        semantic_role = 'Create API'
    elif api['http_method'] == 'POST' and ('update' in api['url'] or 'save' in api['url']):
        semantic_role = 'Update API'
    elif api['http_method'] == 'POST' and ('delete' in api['url'] or 'remove' in api['url'] or 'cancel' in api['url']):
        semantic_role = 'Delete API'
    else:
        semantic_role = 'Action API'

    # Analyze side effects
    side_effects = []
    if api['http_method'] == 'POST':
        if 'create' in api['url'] or 'save' in api['url']:
            side_effects.append('DB_WRITE: Creates new records')
        if 'update' in api['url']:
            side_effects.append('DB_WRITE: Updates existing records')
        if 'delete' in api['url'] or 'remove' in api['url'] or 'cancel' in api['url']:
            side_effects.append('DB_WRITE: Deletes or marks records as deleted')
        if 'pay' in api['url']:
            side_effects.append('EXTERNAL_API: Calls payment gateway')

    # Check for idempotent
    is_idempotent = 'Idempotent' in api['annotations']

    # Generate markdown
    md = f"""# API Semantic Layer - {api['method_name']}

> Auto-generated API Semantic Layer Document
>
> Controller: {controller['name']}
>
> File: `{file_path}`

---

## API Overview

### Basic Information
- **API Name**: {api['method_name']}
- **Description**: {api['comment']}
- **HTTP Method**: {api['http_method']}
- **URL**: `{api['url']}`
- **Business Domain**: {domain}
- **Semantic Role**: {semantic_role}

### Controller Context
- **Controller**: {controller['name']}
- **Controller Description**: {controller['comment']}
- **Package**: {controller['package']}

---

## Part 1: Semantic Layer

### Business Semantics

**What this API does:**
{api['comment']}

**Business Domain:**
- Primary Domain: {domain}
- Responsibility: {_generate_responsibility(api, semantic_role)}

**Semantic Role:**
- Role Type: {semantic_role}
- Operation Type: {'Read' if api['http_method'] == 'GET' else 'Write'}

**Confidence Level:** 0.90
- Based on: URL pattern, HTTP method, method name, and annotations

---

## Part 2: Behavior Layer

### Execution Pattern

**Pattern Type:** REST API Endpoint

**Entry Point:**
- Method: `{controller['name']}.{api['method_name']}()`
- HTTP: `{api['http_method']} {api['url']}`

### Request Parameters

"""

    if api['parameters']:
        for param in api['parameters']:
            md += f"- **{param['name']}** ({param['type']})\n"
    else:
        md += "- No parameters\n"

    md += f"""

### Side Effects

"""

    if side_effects:
        for effect in side_effects:
            md += f"- {effect}\n"
    else:
        md += "- No side effects (Read-only operation)\n"

    md += f"""

### Risk Assessment

**Risk Level:** {'HIGH' if api['http_method'] == 'POST' and side_effects else 'LOW'}

**Reasoning:**
"""

    if api['http_method'] == 'POST':
        md += "- POST operation with potential data modifications\n"
        if side_effects:
            md += f"- {len(side_effects)} side effect(s) identified\n"
    else:
        md += "- GET operation, read-only, no data modification\n"

    md += f"""

### Idempotency

**Is Idempotent:** {'Yes' if is_idempotent else 'No'}

"""

    if is_idempotent:
        md += "This API is marked with @Idempotent annotation, ensuring that multiple identical requests have the same effect as a single request.\n"
    else:
        md += "This API is not explicitly marked as idempotent.\n"

    md += """

---

## Part 3: Context Layer

### Coding Constraints

**Architecture Pattern:**
- Pattern: Spring MVC Controller-Service Architecture
- Layer: Controller Layer (API Entry Point)
- Responsibility: Handle HTTP requests, delegate to service layer

**Naming Convention:**
- Controller: PascalCase with 'Controller' suffix
- Method: camelCase, verb-based naming
- URL: kebab-case with RESTful conventions

**Annotations Used:**
"""

    for annotation in api['annotations']:
        md += f"- @{annotation}\n"

    md += f"""

### Integration Points

**Service Dependencies:**
- This controller delegates business logic to service layer
- Service injection via constructor (Lombok @RequiredArgsConstructor)

**Response Format:**
- Wrapped in `Result<T>` for consistent API response
- Uses `Results.success()` helper for response construction

---

## Part 4: Usage Guide for AI Agent

### When to Use This API

"""

    if api['http_method'] == 'GET':
        md += f"Use this API when you need to {api['comment'].lower()}. This is a read-only operation.\n"
    else:
        md += f"Use this API when you need to {api['comment'].lower()}. This operation modifies data.\n"

    md += f"""

### Example Usage

**Request:**
```http
{api['http_method']} {api['url']}
Content-Type: application/json
```

"""

    if api['parameters'] and api['http_method'] == 'POST':
        md += "**Request Body:**\n```json\n{\n"
        for param in api['parameters']:
            md += f'  "{param["name"]}": "value"\n'
        md += "}\n```\n"

    md += """

**Response:**
```json
{
  "code": "0",
  "message": "success",
  "data": { ... }
}
```

### Important Notes

"""

    if is_idempotent:
        md += "- This API is idempotent - safe to retry on failure\n"

    if api['http_method'] == 'POST':
        md += "- This is a write operation - ensure proper authorization\n"
        md += "- Validate all input parameters before calling\n"

    if 'ILog' in api['annotations']:
        md += "- This API has logging enabled (@ILog)\n"

    md += """

---

## Appendix

### Statistics

- **HTTP Method**: """ + api['http_method'] + """
- **Parameters**: """ + str(len(api['parameters'])) + """
- **Annotations**: """ + str(len(api['annotations'])) + """
- **Side Effects**: """ + str(len(side_effects)) + """

### Related APIs

Check other APIs in the same controller for related functionality.

---

*Generated by AI Agent Semantic Layer System for Java*
"""

    return md


def _generate_responsibility(api: Dict, semantic_role: str) -> str:
    """Generate responsibility description"""
    if semantic_role == 'Query API':
        return f"Retrieve and return {api['comment'].lower()}"
    elif semantic_role == 'Create API':
        return f"Create new records for {api['comment'].lower()}"
    elif semantic_role == 'Update API':
        return f"Update existing records for {api['comment'].lower()}"
    elif semantic_role == 'Delete API':
        return f"Delete or cancel records for {api['comment'].lower()}"
    else:
        return f"Execute action: {api['comment'].lower()}"


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python java_api_analyzer.py <controller_file>")
        sys.exit(1)

    controller_file = sys.argv[1]
    analyzer = JavaAPIAnalyzer(controller_file)
    result = analyzer.analyze()

    print(f"Controller: {result['controller']['name']}")
    print(f"APIs found: {len(result['apis'])}")

    for api in result['apis']:
        print(f"  - {api['http_method']} {api['url']} -> {api['method_name']}")
