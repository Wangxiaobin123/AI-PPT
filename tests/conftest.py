import pytest
from pathlib import Path


@pytest.fixture
def sample_markdown():
    return """# Test Presentation

## Introduction
- Point one
- Point two
- Point three

## Data Overview

| Metric | Q1 | Q2 | Q3 |
|--------|-----|-----|-----|
| Revenue | 100 | 150 | 200 |
| Users | 1000 | 1500 | 2000 |

## Conclusion
Thank you for your attention.
"""


@pytest.fixture
def sample_csv():
    return """Name,Age,City
Alice,30,New York
Bob,25,San Francisco
Charlie,35,Chicago
"""


@pytest.fixture
def sample_html():
    return """<html>
<body>
<h1>Test Document</h1>
<p>This is a test paragraph.</p>
<ul>
<li>Item 1</li>
<li>Item 2</li>
</ul>
<table>
<tr><th>Name</th><th>Value</th></tr>
<tr><td>A</td><td>1</td></tr>
<tr><td>B</td><td>2</td></tr>
</table>
</body>
</html>
"""


@pytest.fixture
def sample_json():
    return '[{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]'


@pytest.fixture
def sample_text():
    return """My Document Title

This is the first paragraph of the document.

This is the second paragraph with more details.

This is the final paragraph.
"""


@pytest.fixture
def output_dir(tmp_path):
    out = tmp_path / "output"
    out.mkdir()
    return str(out)
