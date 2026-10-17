import contextlib
import io
import json
from pathlib import Path
import subprocess
import types
import unittest
from unittest.mock import patch

SKILL = Path(__file__).resolve().parents[1] / 'SKILL.md'
CODE = SKILL.read_text().split('```python\n', 1)[1].split('```', 1)[0]

class SkillExampleTests(unittest.TestCase):
    def run_example(self, response='', rc=0, error=None, query=None, mode=None):
        result = types.SimpleNamespace(returncode=rc, stdout=response, stderr='private diagnostic do not show')
        code = CODE.replace('"the user\'s focused topic"', repr(query)) if query else CODE
        if mode:
            self.assertIn('mode = None', code)
            code = code.replace('mode = None', 'mode = %r' % mode, 1)
        output = io.StringIO()
        with patch('subprocess.run', return_value=result, side_effect=error) as run, contextlib.redirect_stdout(output):
            exec(compile(code, 'skill-example', 'exec'), {})
        return output.getvalue(), run

    def test_unicode_query_is_stdin_and_results_reach_agent(self):
        receipt={'schema':'mimir-artifact-search-v1','status':'ok','evidence':{'results':[{'snippet':'read me'}]}}
        output, run=self.run_example(json.dumps(receipt), query='é'*1500)
        self.assertEqual(json.loads(output),receipt)
        args,kw=run.call_args
        self.assertEqual(args[0][-1],'--tool')
        self.assertEqual(len(args[0]),2)
        self.assertEqual(json.loads(kw['input'])['query'],'é'*1500)
        self.assertLess(len(kw['input'].encode()),8192)
        self.assertEqual(kw['timeout'],50)

    def test_default_request_omits_mode(self):
        receipt={'schema':'mimir-artifact-search-v1','status':'ok','evidence':{'mode':'lexical','results':[]}}
        _,run=self.run_example(json.dumps(receipt))
        self.assertEqual(set(json.loads(run.call_args[1]['input'])),{'query','top'})

    def test_explicit_mode_is_sent_and_fallback_reaches_agent(self):
        for mode in ('hybrid','vector','lexical'):
            with self.subTest(mode=mode):
                receipt={'schema':'mimir-artifact-search-v1','status':'ok','evidence':{'mode':'lexical_fallback','requested_mode':mode,'fallback_reason':'semantic_disabled','results':[{'snippet':'s'}]}}
                output,run=self.run_example(json.dumps(receipt),mode=mode)
                self.assertEqual(json.loads(run.call_args[1]['input'])['mode'],mode)
                self.assertEqual(json.loads(output),receipt)

    def test_skill_states_semantic_limits(self):
        text=' '.join(SKILL.read_text().split())
        for phrase in ('exact terms','paraphrased','weak hits','three-search bound','`hybrid`','do not abstain','not confidence','`lexical_fallback`','retry once without `mode`'):
            self.assertIn(phrase,text)

    def test_no_hits_remains_no_hits(self):
        receipt={'schema':'mimir-artifact-search-v1','status':'no_results','evidence':{'results':[]}}
        output,_=self.run_example(json.dumps(receipt)); self.assertEqual(json.loads(output),receipt)

    def test_invalid_responses_and_nonzero_do_not_expose_diagnostics(self):
        for value in ('not json','null','[]','{"schema":"wrong","status":"ok"}','{"schema":"mimir-artifact-search-v1","status":{}}'):
            with self.subTest(value=value):
                output,_=self.run_example(value);self.assertIn('unavailable',output);self.assertNotIn('diagnostic',output)
        for rc in (1,2,9):
            output,_=self.run_example('private diagnostic',rc=rc); self.assertNotIn('private diagnostic',output)

    def test_missing_and_timeout_are_sanitized(self):
        for error in (OSError('private diagnostic'),subprocess.TimeoutExpired('private diagnostic',50)):
            output,_=self.run_example(error=error);self.assertIn('unavailable',output);self.assertNotIn('private diagnostic',output)

if __name__=='__main__':unittest.main()
