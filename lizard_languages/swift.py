'''
Language parser for Apple Swift
'''

from .code_reader import CodeReader, CodeStateMachine
from .clike import CCppCommentsMixin


class SwiftReader(CodeReader, CCppCommentsMixin):
    # pylint: disable=R0903

    ext = ['swift']
    language_names = ['swift']
    _conditions = set(['if', 'for', 'while', '&&', '||', '?', 'catch',
                      'case', 'guard'])

    def __init__(self, context):
        super(SwiftReader, self).__init__(context)
        self.parallel_states = [SwiftStates(context)]

    @staticmethod
    def generate_tokens(source_code, addition='', token_class=None):
        return CodeReader.generate_tokens(
            source_code,
            r"|\w+\?" +
            r"|\w+\!" +
            r"|\?\?" +
            addition)

    def preprocess(self, tokens):
        tokens = list(t for t in tokens if not t.isspace() or t == '\n')

        def replace_label(tokens, target, replace):
            for i in range(0, len(tokens) - len(target)):
                if tokens[i:i + len(target)] == target:
                    for j in range(0, len(replace)):
                        tokens[i + j] = replace[j]
            return tokens
        for c in (c for c in self.conditions if c.isalpha()):
            tokens = replace_label(tokens, ["(", c, ":"], ["(", "_" + c, ":"])
            tokens = replace_label(tokens, [",", c, ":"], [",", "_" + c, ":"])
        return tokens


class SwiftStates(CodeStateMachine):  # pylint: disable=R0903
    def _state_global(self, token):
        if token == 'func':
            self._state = self._function_name
        if token in ('init', 'subscript'):
            self._function_name(token)
        if token in ('get', 'set', 'willSet', 'didSet', 'deinit'):
            self.context.start_new_function(token)
            self._state = self._expect_function_impl
        if token == 'protocol':
            self._state = self._protocol
        if token in ('let', 'var', 'case', ','):
            self._state = self._expect_declaration_name

    def _expect_declaration_name(self, token):
        if token != '`':
            self._state = self._state_global

    def _function_name(self, token):
        if token != '`':
            self.context.start_new_function(token)
            self._state = self._expect_function_dec

    def _expect_function_dec(self, token):
        if token == '(':
            self._state = self._function_dec

    def _function_dec(self, token):
        if token == ')':
            self._state = self._expect_function_impl
        else:
            self.context.parameter(token)

    def _expect_function_impl(self, token):
        if token == '{':
            self._state = self._function_impl
            self._state(token)

    @CodeStateMachine.read_inside_brackets_then("{}")
    def _function_impl(self, _):
        self._state = self._state_global
        self.context.end_of_function()

    @CodeStateMachine.read_inside_brackets_then("{}")
    def _protocol(self, end_token):
        if end_token == "}":
            self._state = self._state_global
