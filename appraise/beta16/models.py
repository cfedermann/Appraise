from django.contrib.auth.models import User
from django.db import models

"""

tasks
- AbsoluteScoring
- RelativeRanking
--> AdaptiveRanking (sub class for systems with varying word length buckets)



ORM design

- EvalTask
- EvalItem
- EvalData

[TWO different levels]

a) abstract model for evaluation data AND methods

b) actual data, items, results, metadata

===

One EvalTask is comprised of one or more EvalItem instances.
For each of those, we can collect one or more EvalData results.

In our absolute scoring scenario, the requirement for pre-defined
HITs falls aways.  Instead, an EvalTask (= HIT) is pre-loaded with
all k candidate system translations and the respective "reference"
text -- this can be the source, a target reference, or whatever.

Where do we define the "annotation task description"?
Should not be fixed -- this can be used for adequacy, fluency,...

Should an EvalTask be the COMPLETE data for ALL systems for
a SINGLE language pair?  Basically, a pool of data, with an
associated eval question and logical sub units (EvalItem objs)
and related results (EvalData objs).

[reference] <-- [candidate] <-- [datapoint]

Basically, loading all refs and associating candidate segments
gives us a clean ORM layer. We can then create a reverse-sorted
list of references (by increasing number of associated data points)
and process

"""


class MetaData(models.Model):
    """
    Stores object-specific metadata such as annotation start/end time.
    """
    start_time = models.DateTimeField(
      help_text='Annotation start time',
      verbose_name='start time',
      blank=True,
      null=True,
      editable=False
    )

    end_time = models.DateTimeField(
      help_text='Annotation end time',
      verbose_name='end time',
      blank=True,
      null=True,
      editable=False
    )

    users = models.ManyToManyField(
      User,
      blank=True,
      db_index=True,
      null=True,
      help_text="Users who work on this task"
    )

    active = models.BooleanField(
      db_index=True,
      default=True,
      help_text="Indicates that this task is still in use",
      verbose_name="active?"
    )

    mturk_only = models.BooleanField(
      db_index=True,
      default=False,
      help_text="Indicates that this task is only usable via MTurk",
      verbose_name="MTurk only?"
    )

    completed = models.BooleanField(
      db_index=True,
      default=False,
      help_text="Indicates that this task is completed",
      verbose_name="completed?"
    )

    class Meta:
        verbose_name='Meta data'
        verbose_name_plural='Meta data'


class AbsoluteScoringTask(models.Model):
    """
    Implements a multi-system-enabled version of Yvette Graham's
    absolute scoring approach for manual evaluation of MT output.

    The main difference is that we apply the aboslute scoring
    approach in a way which makes it easier to generate valid
    pairwise comparisons.  In the original paper, absolute scores
    are not strictly comparable.  To fix this, we emulate pairwise
    comparison by collecting a total of k absolute scores of a
    set of k candidate systems -- IN (RANDOMIZED) SEQUENCE.

    In theory, this should mean that absolute scores are somewhat
    comparable as they have been assigned in the same "cognitive"
    state of the same human annotator.  We'll have to verify this!
    """
    system_id = models.CharField(
      help_text='Candidate system ID',
      verbose_name='system ID',
      max_length=255
    )

    reference = models.TextField(
      help_text='Used to assess quality of the given candidate',
      verbose_name='reference text'
    )

    candidate = models.TextField(
      help_text='Candidate system output',
      verbose_name='candidate text'
    )

    source_language = models.CharField(
      help_text='ISO 639-2 code for the source language',
      verbose_name='source language',
      max_length=10
    )

    target_language = models.CharField(
      help_text='ISO 639-2 code for the target language',
      verbose_name='target language',
      max_length=10
    )

    segment_id = models.IntegerField(
      help_text='Numeric segment ID, -1 denotes unknown ID',
      verbose_name='segment ID',
      default=-1
    )

    metadata = models.ForeignKey(
      MetaData,
      help_text='Metadata related to this task',
      verbose_name='metadata',
      blank=True,
      null=True
    )

    def __unicode__(self):
        _unicode = u'<task source="{0}" target="{1}" segment="{2}" />'.format(
          self.source_language, self.target_language, self.segment_id
        )
        return _unicode


class AbsoluteScoringData(models.Model):
    """
    Stores the result for an AbsoluteScoringTask instance.
    """
    task = models.ForeignKey(
      AbsoluteScoringTask,
      help_text='AbsoluteScoringTask instance this data relates to',
      verbose_name='related task'
    )

    user = models.ForeignKey(
      User,
      help_text='User instance this data relates to',
      verbose_name='related user'
    )

    score = models.IntegerField(
      help_text='Numeric score for the related task [0-100], -1 denotes unset',
      verbose_name='score',
      default=-1
    )

    is_check = models.BooleanField(
      help_text='Denotes whether this is a consistency check result',
      verbose_name='consistency check?'
    )

    class Meta:
        verbose_name='absolute scoring data'
        verbose_name_plural='absolute scoring data'

    def __unicode__(self):
        _unicode = u'<score user="{0}" task="{1}" value="{2}" />'.format(
          self.user.username, self.task.id, self.score
        )
        return _unicode
