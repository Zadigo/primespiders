import logging
import os
import sys
from subprocess import call

import pytest

os.environ.setdefault('DEBUG', 'True')

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

@pytest.mark.integration
def test_command_start_spider():
    call(['python', '../primespiders/src/primespiders', 'bershka'], stdout=sys.stdout, stderr=sys.stdout)
