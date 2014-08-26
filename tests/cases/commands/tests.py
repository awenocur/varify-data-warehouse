import os
from django.contrib.auth.models import User
from django.core import management
from django.test import TestCase
from django.test.utils import override_settings
from vdw.assessments.models import Assessment, Pathogenicity, ParentalResult, \
    AssessmentCategory
from vdw.samples.models import Sample, CohortSample, Result, SampleRun, \
    SampleManifest, Project, Cohort, Batch, CohortVariant, ResultScore
from vdw.variants.models import Variant
from ..base import QueueTestCase

TESTS_DIR = os.path.join(os.path.dirname(__file__), '../..')
SAMPLE_DIRS = [os.path.join(TESTS_DIR, 'samples', 'batch1')]


@override_settings(VARIFY_SAMPLE_DIRS=SAMPLE_DIRS)
class DeleteTestCase(QueueTestCase):
    def setUp(self):
        super(DeleteTestCase, self).setUp()

        # Immediately validates and creates a sample
        management.call_command('samples', 'queue',
                                startworkers=True)

        # Create and record some data that will be used to create knowledge
        # capture assessments later on.
        self.pathogenicity = Pathogenicity(name='pathogenic')
        self.pathogenicity.save()
        self.parental_result = ParentalResult(name='heterozygous')
        self.parental_result.save()
        self.category = AssessmentCategory(name='other')
        self.category.save()
        self.user = User.objects.all()[0]

    def test_delete(self):
        sample_id = Sample.objects.get(batch__name='batch1', name='NA12891').id

        # Associate some knowledge capture with a sample result for the sample
        # we are trying to delete.
        sample_result = Result.objects.filter(sample_id=sample_id)[0]
        assessment = Assessment(sample_result=sample_result, user=self.user,
                                assessment_category=self.category,
                                sanger_requested=True,
                                pathogenicity=self.pathogenicity,
                                father_result=self.parental_result,
                                mother_result=self.parental_result)
        assessment.save()

        # Since there is an assessment on the sample it should not be deleted
        # by the delete-sample command.
        pre_delete_sample_count = Sample.objects.count()
        management.call_command('samples', 'delete-sample', sample_id)
        self.assertEqual(pre_delete_sample_count, Sample.objects.count())

        # Delete the assessment so that the next delete-sample command issuance
        # will result in the removal of the sample and associated elements.
        Assessment.objects.filter(id=assessment.id).delete()

        # Get the count of all the items we expect to delete with the keys
        # being the table we are deleting from the value being the count we
        # expect to remove.
        sample_counts = {
            'cohort_sample':
            CohortSample.objects.filter(set_object__id=sample_id).count(),
            'sample_result':
            Result.objects.filter(sample__id=sample_id).count(),
            'sample_run':
            SampleRun.objects.filter(sample__id=sample_id).count(),
            'sample_manifest':
            SampleManifest.objects.filter(sample__id=sample_id).count(),
        }

        # Get the initial count of the tables we will be deleting from with
        # the keys being the table we are deleting from and the values being
        # the number of rows initially in the table before the delete command.
        counts = {
            'cohort_sample': CohortSample.objects.count(),
            'sample_result': Result.objects.count(),
            'sample_run': SampleRun.objects.count(),
            'sample_manifest': SampleManifest.objects.count(),
            'sample': Sample.objects.count()
        }

        management.call_command('samples', 'delete-sample', sample_id)

        # Make sure that all the counts after the delete match the initial
        # count less the expected number of deletions.
        self.assertEqual(
            counts['cohort_sample'] - sample_counts['cohort_sample'],
            CohortSample.objects.count())
        self.assertEqual(
            counts['sample_result'] - sample_counts['sample_result'],
            Result.objects.count())
        self.assertEqual(counts['sample_run'] - sample_counts['sample_run'],
                         SampleRun.objects.count())
        self.assertEqual(
            counts['sample_manifest'] - sample_counts['sample_manifest'],
            SampleManifest.objects.count())
        self.assertEqual(counts['sample'] - 1, Sample.objects.count())

        # Check the project delete method here instead of in a new test to
        # prevent a reload of the data from happening.
        project_id = Project.objects.all()[0].id

        # Associate some knowledge capture with a sample result for a sample
        # within the project we are trying to delete.
        sample_result = Result.objects.filter(sample__project_id=project_id)[0]
        assessment = Assessment(sample_result=sample_result, user=self.user,
                                assessment_category=self.category,
                                sanger_requested=True,
                                pathogenicity=self.pathogenicity,
                                father_result=self.parental_result,
                                mother_result=self.parental_result)
        assessment.save()

        # Since there is an assessment on a sample in the project, the project
        # and all samples in it should not be deleted by the delete-project
        # command.
        pre_delete_sample_count = Sample.objects.count()
        pre_delete_project_count = Project.objects.count()
        management.call_command('samples', 'delete-project', project_id)
        self.assertEqual(pre_delete_sample_count, Sample.objects.count())
        self.assertEqual(pre_delete_project_count, Project.objects.count())

        # Delete the assessment so that the next delete-project command
        # issuance will result in the removal of the project and associated
        # elements.
        Assessment.objects.filter(id=assessment.id).delete()

        management.call_command('samples', 'delete-project', project_id)

        # Check that deleting the project cleared out all the rest of
        # the samples and their data.
        self.assertEqual(0, CohortVariant.objects.count())
        self.assertEqual(0, CohortSample.objects.count())
        # We expect 1 cohort remaining because there is a 'World' cohort that
        # is not associated with any project.
        self.assertEqual(1, Cohort.objects.count())
        self.assertEqual(0, Result.objects.count())
        self.assertEqual(0, SampleRun.objects.count())
        self.assertEqual(0, SampleManifest.objects.count())
        self.assertEqual(0, Sample.objects.count())
        self.assertEqual(0, Batch.objects.count())
        self.assertEqual(0, Project.objects.count())


@override_settings(VARIFY_SAMPLE_DIRS=SAMPLE_DIRS)
class AlleleTestCase(QueueTestCase):
    def setUp(self):
        super(AlleleTestCase, self).setUp()

        # Immediately validates and creates a sample
        management.call_command('samples', 'queue',
                                startworkers=True)

    def test_allele_freqs(self):
        management.call_command('samples', 'allele-freqs')
        firstCount = CohortVariant.objects.count()
        self.assertNotEqual(firstCount, 0)
        management.call_command('samples', 'allele-freqs')
        self.assertEqual(firstCount, CohortVariant.objects.count())


@override_settings(VARIFY_SAMPLE_DIRS=SAMPLE_DIRS)
class BigAutoFieldsTestCase(TestCase):
    def setUp(self):
        self.project = Project(id=1, name='', label='')
        self.project.save()
        self.batch = Batch(id=1, name='', project_id=self.project.id, label='')
        self.batch.save()

    def test_big_auto_fields(self):
        # Test that BigAutoFields can exceed Django's default integer limit
        result_count_before = Result.objects.count()
        cohort_variant_count_before = CohortVariant.objects.count()
        two_hundred_billion = int(200e9)

        new_sample = Sample.objects.create(
            id=1, label='', batch_id=self.batch.id, version=1,
            count=1, published=True, name='', project_id=self.project.id)

        new_variant = Variant.objects.create(
            id=1, chr_id=1, pos=1, ref='', alt='', md5='')

        new_result = Result.objects.create(
            id=two_hundred_billion, sample_id=new_sample.id,
            allele_1_id=new_variant.id)

        ResultScore.objects.create(
            id=1, result_id=new_result.id, rank=0, score=0)

        CohortVariant.objects.create(
            id=two_hundred_billion, variant_id=new_variant.id, cohort_id=1)

        result_count_after = Result.objects.count()
        cohort_variant_count_after = CohortVariant.objects.count()

        self.assertEqual(result_count_before + 1, result_count_after)
        self.assertEqual(cohort_variant_count_before + 1,
                         cohort_variant_count_after)
