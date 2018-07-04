# -*- coding: utf8 -*-
import re
from jinja2.filters import do_striptags, do_truncate, do_mark_safe


def myhtmlstrip(astring,n=3):
    '''
        strip the article.body to n <p> elements in index.html
    '''
    # match the contents of style in img tags
    imgstyle = re.compile(r'(?P<imgtag>\s*img[^>].*?style=)(?P<quote>[\'\"]).*?(?P=quote)', re.I)
    # sub the contents of style in img tags with "width:100%;"
    s = imgstyle.sub('\g<imgtag>\g<quote>max-width:100%;\g<quote>', astring)
    # find all the <p> elements except <p>&nbsp;</p>
    s = re.sub(r'<p>\&nbsp;</p>', '', s, re.M)
    para = re.compile(r'<\s*p[^>]*>.*?<\s*/\s*p\s*>', re.I)
    P = re.findall(para, s)
    # remove all html tags for safe
    P = map(do_striptags, P)
    # join the first n items
    P = "</p><p>".join(P[:n])
    # if no <p> elements, do_truncate
    P = do_mark_safe("<p>%s</p>" % P) if P else do_truncate(do_striptags(s), 255, True)
    return P


def mytimestrip(astring):
    '''
        strip article.created_in_words to Chinese in index.html
    '''
    s = re.split("and", astring)
    s = s[0]
    s = re.split(",", s)
    s = s[0]
    s = re.sub(r"seconds?", u"秒前", s, re.I)
    s = re.sub(r"minutes?", u"分钟前", s, re.I)
    s = re.sub(r"hours?", u"小时前", s, re.I)
    s = re.sub(r"days?", u"天前", s, re.I)
    s = re.sub(r"months?", u"个月前", s, re.I)
    return s


def mycreatedstrip(astring):
    '''
        strip article.created to YYYY-MM-DD
    '''
    return do_truncate(astring, 10, True, '')
