from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from .models import ExerciseSubmission, LearningActivity, LearningProgress, LearningTopic, QuizAttempt


class LearningCentreTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='lesson-user', password='safe-test-password-42')
        self.other = get_user_model().objects.create_user(username='other-lesson-user', password='safe-test-password-42')
        self.client = APIClient(); self.client.force_authenticate(self.user)

    def test_catalog_contains_only_error_debugging_lessons_and_filters(self):
        response=self.client.get('/api/v1/learning/')
        self.assertEqual(len(response.data), 36)
        self.assertEqual(set(item['category'] for item in response.data), {'fundamentals','traces','databases','api_http','django_backend','frontend_js','deployment','verification'})
        self.assertTrue(LearningTopic.objects.filter(category__in=['python','java','javascript','react','linux','git']).exists())
        response=self.client.get(reverse('learning_topics'),{'q':'NameError','difficulty':'beginner'})
        self.assertEqual(response.status_code,200); self.assertTrue(any('NameError' in item['title'] for item in response.data))
        self.assertNotIn('practice_answer',response.data[0])
        anonymous=APIClient().get(reverse('learning_topics'))
        self.assertEqual(anonymous.status_code,401)

    def test_detail_keeps_answer_keys_private_until_submission(self):
        topic=LearningTopic.objects.get(error_name='NameError')
        response=self.client.get(reverse('learning_lesson',args=[topic.id]))
        self.assertEqual(response.status_code,200)
        self.assertNotIn('accepted_terms',str(response.data)); self.assertNotIn('correct_index',str(response.data))
        self.assertIn('hints',response.data); self.assertTrue(response.data['quiz'])

    def test_learning_dashboard_and_listed_lesson_detail_routes_are_live(self):
        dashboard=self.client.get('/api/v1/learning/dashboard/')
        listing=self.client.get('/api/v1/learning/')
        self.assertEqual(dashboard.status_code,200)
        self.assertEqual(listing.status_code,200)
        lesson_id=listing.data[0]['id']
        detail=self.client.get(f'/api/v1/learning/lessons/{lesson_id}/')
        self.assertEqual(detail.status_code,200)
        self.assertEqual(detail.data['id'],lesson_id)
        self.assertEqual(self.client.get('/api/v1/learning/lessons/999999/').status_code,404)

    def test_legacy_learning_records_are_preserved_but_hidden_from_error_catalogue(self):
        legacy=LearningTopic.objects.create(
            title='Legacy course', category='debugging', description='Existing content',
            explanation='Existing explanation', buggy_code='', expected_error='', corrected_code='',
            correction_explanation='', practice_question='', practice_answer='',
        )
        LearningProgress.objects.create(user=self.user,topic=legacy,completed=True,bookmarked=True)
        catalogue=self.client.get('/api/v1/learning/')
        dashboard=self.client.get('/api/v1/learning/dashboard/')
        self.assertEqual(catalogue.status_code,200)
        self.assertNotIn(legacy.id,[item['id'] for item in catalogue.data])
        self.assertEqual(LearningTopic.objects.get(pk=legacy.pk).title,'Legacy course')
        self.assertTrue(LearningProgress.objects.get(user=self.user,topic=legacy).bookmarked)
        self.assertEqual(dashboard.data['total_lessons'],36)
        self.assertEqual(dashboard.data['completed_lessons'],0)
        self.assertEqual(self.client.get(f'/api/v1/learning/lessons/{legacy.id}/').status_code,404)

    def test_exercise_is_validated_and_progress_is_user_scoped(self):
        topic=LearningTopic.objects.get(error_name='NameError')
        payload={'proposed_line':'print(total_price)','root_cause':'NameError because total_price is unresolved in this scope','proposed_fix':'Define total_price before using it','difficulty':'beginner','hints_revealed':1}
        result=self.client.post(reverse('learning_exercise',args=[topic.id]),payload,format='json')
        self.assertEqual(result.status_code,201); self.assertTrue(result.data['solved'])
        self.assertTrue(ExerciseSubmission.objects.get(id=result.data['id']).solved)
        self.assertTrue(LearningProgress.objects.get(user=self.user,topic=topic).completed)
        self.assertEqual(LearningProgress.objects.filter(user=self.other).count(),0)

    def test_incorrect_exercise_does_not_complete_lesson(self):
        topic=LearningTopic.objects.get(error_name='NameError')
        result=self.client.post(reverse('learning_exercise',args=[topic.id]),{'root_cause':'Database unavailable','proposed_fix':'Restart it','difficulty':'beginner','hints_revealed':0},format='json')
        self.assertFalse(result.data['solved']); self.assertFalse(LearningProgress.objects.filter(user=self.user,topic=topic,completed=True).exists())

    def test_bookmark_and_completion_require_validated_fields(self):
        topic=LearningTopic.objects.get(error_name='HTTP 401')
        result=self.client.post(reverse('learning_lesson',args=[topic.id]),{'bookmarked':True},format='json')
        self.assertTrue(result.data['bookmarked']); self.assertFalse(result.data['completed'])
        self.assertEqual(self.client.post(reverse('learning_lesson',args=[topic.id]),{'completed':'yes'},format='json').status_code,400)
        self.assertEqual(self.client.post(reverse('learning_lesson',args=[topic.id]),{'completed':True},format='json').status_code,400)

    def test_quiz_scores_are_computed_and_saved(self):
        topic=LearningTopic.objects.get(error_name='NameError')
        result=self.client.post(reverse('learning_quiz',args=[topic.id]),{'answers':[0]},format='json')
        self.assertEqual(result.data['score'],1); self.assertEqual(result.data['total'],1)
        self.assertEqual(QuizAttempt.objects.get(id=result.data['id']).user,self.user)
        self.assertEqual(self.client.get(reverse('learning_dashboard')).data['quiz_accuracy'],100)

    def test_recommendations_match_detected_error_and_progress_counts_are_real(self):
        result=self.client.get(reverse('learning_recommendations'),{'error_type':'Python NameError','message':"name 'total_price' is not defined"})
        self.assertTrue(result.data['recommendations'])
        self.assertEqual(result.data['recommendations'][0]['lesson']['error_name'],'NameError')
        stats=self.client.get(reverse('learning_dashboard')).data
        self.assertEqual(stats['total_lessons'],36)
        self.assertEqual(stats['completed_lessons'],0)

    def test_existing_learning_activity_is_preserved_and_user_private(self):
        response=self.client.post(reverse('learning_activities'),{'type':'practice','prompt':'What confirms a missing table?','answer':'The database error','completed':True},format='json')
        self.assertEqual(response.status_code,201)
        self.assertEqual(self.client.get(reverse('learning_activities')).data[0]['answer'],'The database error')
        other=APIClient(); other.force_authenticate(self.other)
        self.assertEqual(other.get(reverse('learning_activities')).data,[])
