from agentml.common import bool_attribute
from agentml.parser.tags import Tag


class Command(Tag):

    def value(self):
        """
        Return the current value of a variable
        """
        # Does the variable name have tags to parse?
        if len(self._element):
            command = ''.join(map(str, self.trigger.agentml.parse_tags(self._element, self.trigger)))
        else:
            command = self._element.text

        # Should we replace the return value?
        apply_response = int(bool_attribute(self._element, 'return'))

        return '<#COMMAND#{ret}#{cmd}#>'.format(ret=apply_response, cmd=command.replace('#', '\\#'))
