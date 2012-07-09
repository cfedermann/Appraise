Appraise Evaluation System
==========================

Initial import into GitHub on Oct 23, 2011.

## Update

A new release of the Appraise software package is currently being prepared in time for the [Seventh MT Marathon 2012][1] which will take place September 3-8, 2012 in Edinburgh, Scotland.

## Overview

Appraise is an open-source tool for manual evaluation of Machine Translation output. Appraise allows to collect human judgments on translation output, implementing annotation tasks such as

  1. translation quality checking;
  2. ranking of translations;
  3. error classification;
  4. manual post-editing.

It features an extensible XML import/output format and can easily be adapted to new annotation tasks. The next version of Appraise will also include automatic computation of inter-annotator agreements allowing quick access to evaluation results.

Appraise is available under [an open, BSD-style license][4].

## How does it look like?

You can see [a deployed version of Appraise here][2]. If you want to play around with it, you will need an account in order to login to the system. I'll be happy to create an account for you, just drop me an email `cfedermann [at] dfki [dot] de`.

## System Requirements

Appraise is based on the [Django framework][3]. You will need __Python 2.7__ to run it locally. For deployment, a FastCGI compatible web server such as __lighttpd__ is required.

## Quickstart Instructions

Assuming you have already installed Python and Django, you can clone and start up a local copy of Appraise using the following commands:

    $ git clone git://github.com/cfedermann/Appraise.git Appraise-Software
    ...
    $ cd Appraise-Software/appraise
    $ python manage.py syncdb
    ...
    python manage.py runserver

You should be greeted with the following output from your terminal:

    Validating models...

    0 errors found
    Django version 1.3.1, using settings 'appraise.settings'
    Development server is running at http://127.0.0.1:8000/
    Quit the server with CONTROL-C.

Point your browser to [http://127.0.0.1:8000/appraise/](http://127.0.0.1:8000/appraise/) and there it is...

## References

> __Christian Federmann__
> Appraise: An Open-Source Toolkit for Manual Evaluation of Machine Translation Output
> Submitted to _MT Marathon 2012_ ___(forthcoming)___

> __Christian Federmann__
> Appraise: An Open-Source Toolkit for Manual Phrase-Based Evaluation of Translations
> In _Proceedings of the Seventh Conference on International Language Resources and Evaluation_, Valletta, Malta, LREC, 5/2010

[1]: http://www.statmt.org/mtm12/
[2]: http://www.dfki.de/appraise/
[3]: http://www.djangoproject.com/
[4]: https://raw.github.com/cfedermann/Appraise/master/appraise/LICENSE