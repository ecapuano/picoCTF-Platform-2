"""
Problem Testing Module
"""

import pytest

import api.user
import api.team
import api.common
import api.problem

from api.common import APIException
from common import clear_collections, ensure_empty_collections
from conftest import setup_db, teardown_db

class TestProblems(object):
    """
    API Tests for problem.py
    """
    
    test_user = {
        "username": "valid",
        "password": "valid",
        "email": "test@hs.edu",
        "create-new-team": "on",

        "team-name-new": "test",
        "team-adv-name-new": "test",
        "team-adv-email-new": "hacks@hs.edu",
        "team-school-new": "Hacks HS",
        "team-password-new": "leet_hax"
    }

    # create 5 base problems
    base_problems = [
        {
            "display_name" : "base-" + str(i),
            "score" : 10,
            "category": "",
            "grader" : "test.py",
            "description" : "",
            "threshold" : 0,
        }
        for i in range(5)
    ]

    # create 5 disabled problems
    disabled_problems = [
        {
            "display_name" : "locked-" + str(i),
            "score" : 10,
            "category": "",
            "grader" : "test.py",
            "description" : "",
            "threshold" : 0,
            "disabled": True
        }
        for i in range(5)
    ]

    def generate_problems(base_problems):
        """A workaround for python3's list comprehension scoping"""

        # create 5 level1 problems
        level1_problems = [
            {
                "display_name" : "level1-" + str(i),
                "score" : 60,
                "category": "",
                "grader" : "test.py",
                "description" : "",
                "threshold" : 3,
                "weightmap" : {p['display_name']: 1 for p in base_problems}
            }
            for i in range(5)
        ]

        return level1_problems

    level1_problems = generate_problems(base_problems)

    enabled_problems = base_problems + level1_problems
    all_problems = enabled_problems + disabled_problems

    # test keys
    correct = "test"
    wrong = "wrong"

    def setup_class(self):
        """
        Class setup code
        """

        setup_db()

        # initialization code
        self.uid = api.user.register_user(self.test_user)
        self.tid = api.user.get_team(uid=self.uid)['tid']

        # insert all problems
        self.pids = []
        for problem in self.all_problems:
            pid = api.problem.insert_problem(problem)
            self.pids.append(pid)

    def teardown_class(self):
        teardown_db()

    def test_insert_problems(self):
        """
        Tests problem insertion.

        Covers:
            problem.insert_problem
            problem.get_problem
            problem.get_all_problems
        """

        # problems were inserted in initialization - try to insert the problems again
        for problem in self.all_problems:
            with pytest.raises(APIException):
                api.problem.insert_problem(problem)
                assert False, "Was able to insert a problem twice."

        # verify that the problems match
        db_problems = api.problem.get_all_problems()
        assert all([p in self.enabled_problems for p in db_problems]), "Problems do not match"

        db_all_problems = api.problem.get_all_problems(show_disabled=True)
        assert all([p in self.all_problems for p in db_all_problems]), "Disabled problems do not match"

    @ensure_empty_collections("submissions")
    @clear_collections("submissions")
    def test_submissions(self):
        """
        Tests key submissions.

        Covers:
            problem.submit_key
            problem.get_submissions
            problem.get_team_submissions
        """

        # test correct submissions
        for problem in self.base_problems[:2]:
            result = api.problem.submit_key(self.tid, problem['pid'], self.correct, uid=self.uid)
            assert result['correct'], "Correct key was not accepted"
            assert result['points'] == problem['score'], "Did not return correct score"

            solved = api.problem.get_solved_problems(self.tid)
            assert api.problem.get_problem(pid=problem['pid']) in solved

        # test incorrect submissions
        for problem in self.base_problems[2:]:
            result = api.problem.submit_key(self.tid, problem['pid'], self.wrong, uid=self.uid)
            assert not result['correct'], "Incorrect key was accepted"
            assert result['points'] == problem['score'], "Did not return correct score"

            solved = api.problem.get_solved_problems(self.tid)
            assert api.problem.get_problem(pid=problem['pid']) not in solved

        # test submitting correct twice
        with pytest.raises(APIException):
            api.problem.submit_key(self.tid, self.base_problems[0]['pid'], self.correct, uid=self.uid)
            assert False, "Submitted key to problem that was already solved"

        # test submitting to disabled problem
        with pytest.raises(APIException):
            api.problem.submit_key(self.tid, self.disabled_problems[0]['pid'], self.correct, uid=self.uid)
            assert False, "Submitted key to disabled problem"

        # test getting submissions two ways
        assert len(api.problem.get_submissions(uid=self.uid)) == len(self.base_problems)
        assert len(api.problem.get_submissions(tid=self.tid)) == len(self.base_problems)

    @ensure_empty_collections("submissions")
    @clear_collections("submissions")
    def test_get_unlocked_problems(self):
        """
        Tests getting the unlocked problems

        Covers:
            problem.get_unlocked_problems
            problem.submit_key
        """

        # check that base problems are unlocked
        unlocked = api.problem.get_unlocked_problems(self.tid)
        assert all([p in unlocked for p in self.base_problems]), "Base problems are not initially unlocked!"

        # unlock more problems
        for problem in self.base_problems[:3]:
            api.problem.submit_key(self.tid, problem['pid'], self.correct, uid=self.uid)

        unlocked = api.problem.get_unlocked_problems(self.tid)
        assert all([p in unlocked for p in self.base_problems + self.level1_problems]), "Level1 problems didn't unlock"
        assert all([p not in unlocked for p in self.disabled_problems]), "Disabled problems are unlocked"