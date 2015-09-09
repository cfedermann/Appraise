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
    reference = models.TextField(
      help_text='Used to assess quality of the given candidate',
      verbose_name='Reference text'
    )

    candidate = models.TextField(
      help_text='Candidate system output',
      verbose_name='Candidate text'
    )

    source_language = models.CharField(
      help_text='ISO 639-2 code for the source language',
      verbose_name='Source language',
      max_length=10
    )

    target_language = models.CharField(
      help_text='ISO 639-2 code for the target language',
      verbose_name='Target language',
      max_length=10
    )

    segment_id = models.IntegerField(
      help_text='Numeric segment ID, -1 denotes unknown ID',
      verbose_name='Segment ID',
      default=-1
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
      verbose_name='Related task'
    )

    user = models.ForeignKey(
      User,
      help_text='User instance this data relates to',
      verbose_name='Related user'
    )

    score = models.IntegerField(
      help_text='Numeric score for the related task [0-100], -1 denotes unset',
      verbose_name='Score',
      default=-1
    )

    class Meta:
        verbose_name='Absolute scoring data'
        verbose_name_plural='Absolute scoring data'

    def __unicode__(self):
        _unicode = u'<score user="{0}" task="{1}" value="{2}" />'.format(
          self.user.username, self.task.id, self.score
        )
        return _unicode
