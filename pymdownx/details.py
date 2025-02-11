"""
Details.

pymdownx.details

MIT license.

Copyright (c) 2017 Isaac Muse <isaacmuse@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
documentation files (the "Software"), to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions
of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
DEALINGS IN THE SOFTWARE.
"""
from markdown import Extension
from markdown.blockprocessors import BlockProcessor
import xml.etree.ElementTree as etree
import re


class DetailsProcessor(BlockProcessor):
    """Details block processor."""

    START = re.compile(
        r'(?:^|\n)\?{3}(\+)? ?(?:([\w\-]+(?: +[\w\-]+)*?)?(?: +"(.*?)")|([\w\-]+(?: +[\w\-]+)*?)) *(?:\n|$)'
    )
    COMPRESS_SPACES = re.compile(r' {2,}')

    def __init__(self, parser):
        """Initialization."""

        super().__init__(parser)

        self.current_sibling = None
        self.content_indention = 0

    def detab_by_length(self, text, length):
        """Remove a tab from the front of each line of the given text."""

        newtext = []
        lines = text.split('\n')
        for line in lines:
            if line.startswith(' ' * length):
                newtext.append(line[length:])
            elif not line.strip():
                newtext.append('')  # pragma: no cover
            else:
                break
        return '\n'.join(newtext), '\n'.join(lines[len(newtext):])

    def parse_content(self, parent, block):
        """Get sibling details.

        Retrieve the appropriate sibling element. This can get tricky when
        dealing with lists.

        """

        old_block = block
        non_details = ''

        # We already acquired the block via test
        if self.current_sibling is not None:
            sibling = self.current_sibling
            block, non_details = self.detab_by_length(block, self.content_indent)
            self.current_sibling = None
            self.content_indent = 0
            return sibling, block, non_details

        sibling = self.lastChild(parent)

        if sibling is None or sibling.tag.lower() != 'details':
            sibling = None
        else:
            # If the last child is a list and the content is indented sufficient
            # to be under it, then the content's is sibling is in the list.
            last_child = self.lastChild(sibling)
            indent = 0
            while last_child is not None:
                if (
                    sibling is not None and block.startswith(' ' * self.tab_length * 2) and
                    last_child is not None and last_child.tag in ('ul', 'ol', 'dl')
                ):

                    # The expectation is that we'll find an `<li>`.
                    # We should get it's last child as well.
                    sibling = self.lastChild(last_child)
                    last_child = self.lastChild(sibling) if sibling is not None else None

                    # Context has been lost at this point, so we must adjust the
                    # text's indentation level so it will be evaluated correctly
                    # under the list.
                    block = block[self.tab_length:]
                    indent += self.tab_length
                else:
                    last_child = None

            if not block.startswith(' ' * self.tab_length):
                sibling = None

            if sibling is not None:
                indent += self.tab_length
                block, non_details = self.detab_by_length(old_block, indent)
                self.current_sibling = sibling
                self.content_indent = indent

        return sibling, block, non_details

    def test(self, parent, block):
        """Test block."""

        if self.START.search(block):
            return True
        else:
            return self.parse_content(parent, block)[0] is not None

    def run(self, parent, blocks):
        """Convert to details/summary block."""

        block = blocks.pop(0)
        m = self.START.search(block)

        if m:
            # remove the first line
            if m.start() > 0:
                self.parser.parseBlocks(parent, [block[:m.start()]])
            block = block[m.end():]
            block, non_details = self.detab(block)
        else:
            sibling, block, non_details = self.parse_content(parent, block)

        if m:
            state = m.group(1)
            is_open = state is not None

            if m.group(4):
                class_name = self.COMPRESS_SPACES.sub(' ', m.group(4).lower())
                title = class_name.split(' ')[0].capitalize()
            else:
                classes = m.group(2)
                class_name = '' if classes is None else self.COMPRESS_SPACES.sub(' ', classes.lower())
                title = m.group(3)

            div = etree.SubElement(parent, 'details', ({'open': 'open'} if is_open else {}))
            if class_name:
                div.set('class', class_name)
            summary = etree.SubElement(div, 'summary')
            summary.text = title
        else:
            # Sibling is a list item, but we need to wrap it's content should be wrapped in <p>
            if sibling.tag in ('li', 'dd') and sibling.text:
                text = sibling.text
                sibling.text = ''
                p = etree.SubElement(sibling, 'p')
                p.text = text

            div = sibling

        self.parser.parseChunk(div, block)

        if non_details:
            # Insert the non-details content back into blocks
            blocks.insert(0, non_details)


class DetailsExtension(Extension):
    """Add Details extension."""

    def extendMarkdown(self, md):
        """Add Details to Markdown instance."""
        md.registerExtension(self)

        md.parser.blockprocessors.register(DetailsProcessor(md.parser), "details", 105)


def makeExtension(*args, **kwargs):
    """Return extension."""

    return DetailsExtension(*args, **kwargs)
