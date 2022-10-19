import importlib
import inspect
import re
import secrets
import sys
import textwrap
from dataclasses import dataclass
from types import FunctionType
from typing import Any, Optional

import pytest
from _pytest.assertion.rewrite import AssertionRewritingHook

passing_files = {
    'test_abc.py',
    'test_callable.py',
    'test_recursion.py',
    'test_rich_repr.py',
    'test_structural_pattern_matching.py',
    'test_version.py',
    'test_networks.py',
    'test_networks_ipaddress.py',
    'test_color.py',
    'test_types.py',
    'test_datetime.py',
    'test_types_payment_card_number.py',
    'test_main.py',
    'test_utils.py',
    'test_typing.py',
}


def pytest_collection_modifyitems(items):
    for item in items:
        if item.parent.name not in passing_files:
            item.add_marker('xfail')


def _extract_source_code_from_function(function):
    if function.__code__.co_argcount:
        raise RuntimeError(f'function {function.__qualname__} cannot have any arguments')

    code_lines = ''
    body_started = False
    for line in textwrap.dedent(inspect.getsource(function)).split('\n'):
        if line.startswith('def '):
            body_started = True
            continue
        elif body_started:
            code_lines += f'{line}\n'

    return textwrap.dedent(code_lines)


def _create_module_file(code, tmp_path, name):
    name = f'{name}_{secrets.token_hex(5)}'
    path = tmp_path / f'{name}.py'
    path.write_text(code)
    return name, str(path)


@pytest.fixture
def create_module(tmp_path, request):
    def run(source_code_or_function, rewrite_assertions=True):
        """
        Create module object, execute it and return
        Can be used as a decorator of the function from the source code of which the module will be constructed

        :param source_code_or_function string or function with body as a source code for created module
        :param rewrite_assertions: whether to rewrite assertions in module or not

        """
        if isinstance(source_code_or_function, FunctionType):
            source_code = _extract_source_code_from_function(source_code_or_function)
        else:
            source_code = source_code_or_function

        module_name, filename = _create_module_file(source_code, tmp_path, request.node.name)

        if rewrite_assertions:
            loader = AssertionRewritingHook(config=request.config)
            loader.mark_rewrite(module_name)
        else:
            loader = None

        spec = importlib.util.spec_from_file_location(module_name, filename, loader=loader)
        sys.modules[module_name] = module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    return run


@dataclass
class Err:
    message: str
    errors: Optional[Any] = None

    def __repr__(self):
        if self.errors:
            return f'Err({self.message!r}, errors={self.errors!r})'
        else:
            return f'Err({self.message!r})'

    def message_escaped(self):
        return re.escape(self.message)
