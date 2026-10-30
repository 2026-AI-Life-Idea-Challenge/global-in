"""Profile adapter contracts; no real DB connection or external calls."""

from copy import deepcopy
import unittest
from unittest.mock import patch

from app.models.user_profile import UserProfile
from app.retrieval import program_search
from app.services import profile_program_search as service


class ProfileProgramSearchTests(unittest.TestCase):
    def test_maps_filters_and_preserves_result_without_mutating_profile(self):
        profile = UserProfile(
            target_country="australia", target_visa_type="working_holiday",
            purpose="study later", nationalities=["KR"], date_of_birth="1998-05-15",
        )
        before = deepcopy(profile.model_dump())
        rows = [{"program_id": "example", "name": "Original DB name",
                 "country": "australia", "category": "working_holiday"}]
        with patch.object(service, "search_programs", return_value=rows) as search:
            result = service.search_programs_for_profile(profile)
        search.assert_called_once_with(
            country="australia", category="working_holiday", limit=20, offset=0,
        )
        self.assertIs(result, rows)
        self.assertEqual(profile.model_dump(), before)

    def test_calls_actual_search_context_method_once(self):
        profile = UserProfile(target_country="canada", target_visa_type="student")
        original = UserProfile.to_search_context
        with patch.object(UserProfile, "to_search_context", autospec=True,
                          side_effect=original) as context, \
                patch.object(service, "search_programs", return_value=[]) as search:
            service.search_programs_for_profile(profile)
        context.assert_called_once_with(profile)
        search.assert_called_once_with(country="canada", category="study", limit=20, offset=0)
        self.assertEqual(profile.target_visa_type, "student")

    def test_only_student_alias_changes(self):
        for visa, category in (("student", "study"), ("study", "study"),
                               ("working_holiday", "working_holiday"),
                               ("employment", "employment")):
            with self.subTest(visa=visa), patch.object(service, "search_programs", return_value=[]) as search:
                service.search_programs_for_profile(UserProfile(target_visa_type=visa))
                search.assert_called_once_with(country=None, category=category, limit=20, offset=0)

    def test_missing_fields_stay_none_without_inference_from_other_fields(self):
        cases = (
            ({}, None, None),
            ({"target_country": "japan"}, "japan", None),
            ({"target_visa_type": "working_holiday"}, None, "working_holiday"),
            ({"purpose": "호주에서 유학", "nationalities": ["KR"]}, None, None),
            ({"target_country": None, "target_visa_type": None}, None, None),
        )
        for fields, country, category in cases:
            with self.subTest(fields=fields), patch.object(service, "search_programs", return_value=[]) as search:
                service.search_programs_for_profile(UserProfile(**fields))
                search.assert_called_once_with(country=country, category=category, limit=20, offset=0)

    def test_forwards_explicit_pagination(self):
        for limit, offset in ((1, 0), (100, 3), (17, 5)):
            with self.subTest(limit=limit, offset=offset), \
                    patch.object(service, "search_programs", return_value=[]) as search:
                service.search_programs_for_profile(UserProfile(), limit=limit, offset=offset)
                search.assert_called_once_with(country=None, category=None, limit=limit, offset=offset)

    def test_empty_results_are_returned_unchanged(self):
        rows = []
        with patch.object(service, "search_programs", return_value=rows):
            self.assertIs(service.search_programs_for_profile(UserProfile()), rows)

    def test_bad_filters_use_existing_validation_before_db(self):
        cases = (
            [("target_country", value) for value in ("", " \t", "unknown", "Australia", " canada ")]
            + [("target_visa_type", value) for value in ("", " \t", "tourist", "Student", "student ", " study ")]
        )
        with patch.object(program_search, "get_connection") as db:
            for field, value in cases:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    service.search_programs_for_profile(UserProfile(**{field: value}))
        db.assert_not_called()

    def test_bad_pagination_uses_existing_validation_before_db(self):
        cases = (
            [{"limit": value} for value in (0, 101, True, False, 1.5, "20", None)]
            + [{"offset": value} for value in (-1, True, False, 1.5, "0", None)]
        )
        with patch.object(program_search, "get_connection") as db:
            for changes in cases:
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    service.search_programs_for_profile(UserProfile(), **changes)
        db.assert_not_called()

    def test_non_profile_input_is_rejected_before_search(self):
        with patch.object(service, "search_programs") as search:
            for value in (None, {}, "australia", True, 1):
                with self.subTest(value=value), self.assertRaises(ValueError):
                    service.search_programs_for_profile(value)
        search.assert_not_called()

    def test_search_errors_propagate_without_becoming_empty_results(self):
        failure = RuntimeError("search failed")
        with patch.object(service, "search_programs", side_effect=failure), \
                self.assertRaises(RuntimeError) as caught:
            service.search_programs_for_profile(UserProfile())
        self.assertIs(caught.exception, failure)


if __name__ == "__main__":
    unittest.main()
