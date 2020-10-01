import pytest
from py.xml import html

#def pytest_html_results_summary(prefix, summary, postfix):
#    prefix.extend([html.h1("A GOOD TITLE")])


def pytest_html_report_title(report):
   report.title = "WEPN Report Summary"

