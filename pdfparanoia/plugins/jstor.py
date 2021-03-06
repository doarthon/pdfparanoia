# -*- coding: utf-8 -*-

from copy import copy

import sys

from ..parser import parse_content
from ..eraser import (
    replace_object_with,
)
from ..plugin import Plugin

from pdfminer.pdftypes import PDFObjectNotFound

class JSTOR(Plugin):
    """
    JSTOR
    ~~~~~~~~~~~~~~~

    JSTOR watermarks a first page with an "Accessed" date, lots of TC barf, and
    then also a watermark at the bottom of each page with a timestamp.

    Watermarks removed:
        * "Accessed" timestamp on the front page
        * footer watermarks on each page

    This was primary written for JSTOR pdfs generated by:
         /Producer (itext-paulo-155 \(itextpdf.sf.net-lowagie.com\))
    """

    # these terms appear on a page that has been watermarked
    requirements = [
        "All use subject to ",
        "JSTOR Terms and Conditions",
        "This content downloaded  on",
    ]

    @classmethod
    def scrub(cls, content, verbose=0):
        replacements = []

        # jstor has certain watermarks only on the first page
        page_id = 0

        # parse the pdf into a pdfminer document
        pdf = parse_content(content)

        # get a list of all object ids
        xref = pdf.xrefs[0]
        objids = xref.get_objids()

        # check each object in the pdf
        for objid in objids:
            # get an object by id
            try:
                obj = pdf.getobj(objid)

                if hasattr(obj, "attrs"):
                    if obj.attrs.has_key("Filter") and str(obj.attrs["Filter"]) == "/FlateDecode":
                        data = copy(obj.get_data())

                        # make sure all of the requirements are in there
                        if all([requirement in data for requirement in JSTOR.requirements]):
                            better_content = data

                            # remove the date
                            startpos = better_content.find("This content downloaded ")
                            endpos = better_content.find(")", startpos)
                            segment = better_content[startpos:endpos]
                            if verbose >= 2 and replacements:
                                sys.stderr.write("%s: Found object %s with %r: %r; omitting..." % (cls.__name__, objid, cls.requirements, segment))

                            better_content = better_content.replace(segment, "")

                            # it looks like all of the watermarks are at the end?
                            better_content = better_content[:-160]

                            # "Accessed on dd/mm/yyy hh:mm"
                            #
                            # the "Accessed" line is only on the first page
                            #
                            # it's based on /F2
                            #
                            # This would be better if it could be decoded to
                            # actually search for the "Accessed" text.
                            if page_id == 0 and "/F2 11 Tf\n" in better_content:
                                startpos = better_content.rfind("/F2 11 Tf\n")
                                endpos = better_content.find("Tf\n", startpos+5)

                                if verbose >= 2 and replacements:
                                    sys.stderr.write("%s: Found object %s with %r: %r; omitting..." % (cls.__name__, objid, cls.requirements, better_content[startpos:endpos]))

                                better_content = better_content[0:startpos] + better_content[endpos:]

                            replacements.append([objid, better_content])

                            page_id += 1
            except PDFObjectNotFound, e:
                print >>sys.stderr, 'Missing object: %r' % e

        if verbose >= 1 and replacements:
            sys.stderr.write("%s: Found objects %s with %r; omitting..." % (cls.__name__, [deets[0] for deets in replacements], cls.requirements))

        for deets in replacements:
            objid = deets[0]
            replacement = deets[1]
            content = replace_object_with(content, objid, replacement)

        return content

