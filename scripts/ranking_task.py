# -*- coding: utf-8 -*-

class RankingTask:
    # Patched to work with unicode strings which are produced upstream.
    def __init__(self):
        self.id = None
        self.source = None
        self.reference = None
        self.system_names = None
        self.system_outputs = None

    def __init__(self, id, source, ref, names, outputs):
        self.id = id
        self.source = source
        self.reference = ref
        self.system_names = names
        self.system_outputs = outputs

    def attr(self):
        return u''

    def xml(self, indent=4):
        _str  = u'\n    <seg{0}>'.format(self.attr())
        _str += u'\n      <source id="{0}">{1}</source>'.format(self.id, self.source)
        _str += u'\n      <reference>{0}</reference>'.format(self.reference)
        for i in range(len(self.system_names)):
            _str += u'\n      <translation system="{0}">{1}</translation>'.format(self.system_names[i], self.system_outputs[i])
        _str += u'\n    </seg>'

        return _str

class Control(RankingTask):
    """A Control is a RankingTask that happens to have been filled out."""

    @staticmethod
    def load(filename):
        controls = []
        control = None

        fh = open(filename)
        for line in fh:
            line = line.rstrip()
            if line.startswith('SENTENCE '):
                control = Control()
                control.id = int(line.split()[-1])
            elif line.startswith('SOURCE '):
                control.source = ' '.join(line.split()[1:])
            elif line.startswith('REFERENCE '):
                control.reference = ' '.join(line.split()[1:])
            elif line.startswith('SYSTEMS '):
                control.system_names = line.split()[1:]
                control.system_outputs = [fh.next().rstrip() for x in control.system_names]
                control.ranks = [fh.next().rstrip().split() for x in control.system_names]
                controls.append(control)

        return controls

    def __init__(self):
        self.ranks = None

    def __str__(self):
        s = 'SENTENCE %d\n' % (self.id)
        s += 'SCORE: %d\n' % (self.score())
        s += 'SOURCE %s\n' % (self.source)
        s += 'REFERENCE %s\n' % (self.reference)
        s += 'SYSTEMS %s\n' % (' '.join(self.system_names))
        for output in self.system_outputs:
            s += output + '\n'
        for ranks in self.ranks:
            s += ' '.join(ranks) + '\n'

        return s

    def attr(self):
        return " control='true'"

    def score(self):
        """Returns the score of a control, which is the sum of the absolute values of the differences between opposite ranks."""

        score = 0
        for i,row in enumerate(self.ranks):
            for j in range(i+1, len(row)):
                score += abs(int(self.ranks[i][j]) - int(self.ranks[j][i]))

        return score
