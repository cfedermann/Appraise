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

You can see [a deployed version of Appraise here][2]. If you want to play around with it, you will need an account in order to login to the system. I'll be happy to create an account for you, just drop me an email `cfedermann [at] gmail [dot] com`.

## System Requirements

Appraise is based on the [Django framework][3], version 1.3 or newer. You will need __Python 2.7__ to run it locally. For deployment, a FastCGI compatible web server such as __lighttpd__ is required.

## Quickstart Instructions

Assuming you have already installed Python and Django, you can clone a local copy of Appraise using the following command; you can change the folder name `Appraise-Software` to anything you like.

    $ git clone git://github.com/cfedermann/Appraise.git Appraise-Software
    ...

After having cloned the GitHub project, you have to initialise Appraise. This is a two-step process:

1. Initialise the SQLite database:

        $ cd Appraise-Software/appraise
        $ python manage.py syncdb
        ...

2. Collect static files and copy them into `Appraise-Software/appraise/static-files`. Answer `yes` when asked whether you want to overwrite existing files.

        $ python manage.py collectstatic
        ...

    More information on handling of static files in Django 1.3+ is [available here][5].

Finally, you can start up your local copy of Django using the `runserver` command:

    $ python manage.py runserver

You should be greeted with the following output from your terminal:

    Validating models...

    0 errors found
    Django version 1.3.1, using settings 'appraise.settings'
    Development server is running at http://127.0.0.1:8000/
    Quit the server with CONTROL-C.

Point your browser to [http://127.0.0.1:8000/appraise/](http://127.0.0.1:8000/appraise/) and there it is...

### Add users

Users can be added [here](http://127.0.0.1:8000/appraise/admin/auth/user/add/).

### Add evaluation tasks

Evaluation tasks can be created
[here](http://127.0.0.1:8000/appraise/admin/evaluation/evaluationtask/add/).

You need an XML file in proper format to upload a task; an example file can be found in
examples/sample-ranking-task.xml .

## Deployment with lighttpd

You will need to create a customised `start-server.sh` script inside `Appraise-Software/appraise`. There is a `.sample` file available in this folder which should help you get started quickly. In a nutshell, you have to uncomment and edit the last two lines:

    # /path/to/bin/python manage.py runfcgi host=127.0.0.1 port=1234 method=threaded pidfile=$DJANGO_PID

The first line tells Django to start up in FastCGI mode, binding to hostname `127.0.0.1` and port `1234` in our example, running a `threaded` server and writing the process ID to the file `$DJANGO_PID`. The `.pid` files will be used by `stop-server.sh` to properly shutdown Appraise.

Using Django's `manage.py` with the `runfcgi` command requires you to also install `flup` into the `site-packages` folder of your Python installation. It is available [from here][6].

    # /path/to/sbin/lighttpd -f /path/to/lighttpd/etc/appraise.conf

The second line starts up the `lighttd` server using an appropriate configuration file `appraise.conf`. Have a look at `Appraise-Software/examples/appraise-lighttpd.conf` to create your own.

Once the various `/path/to/XYZ` settings are properly configured, you should be able to launch Appraise in production mode.

## References

If you use Appraise in your research, please cite the MT Marathon 2012 paper:

__Christian Federmann__
Appraise: An Open-Source Toolkit for Manual Evaluation of Machine Translation Output
In _The Prague Bulletin of Mathematical Linguistics volume 98_, Prague, Czech Republic, 9/2012

### BibTex

    @Article{mtm12_appraise,
      author =  {Christian Federmann},
      title =   {Appraise: An Open-Source Toolkit for Manual Evaluation of Machine Translation Output},
      journal = {The Prague Bulletin of Mathematical Linguistics},
      volume =  {98},
      pages =   {25--35},
      year =    {2012},
      address = {Prague, Czech Republic},
      month =   {September}
    }

A previous version of Appraise had been published at LREC 2010:

__Christian Federmann__
Appraise: An Open-Source Toolkit for Manual Phrase-Based Evaluation of Translations
In _Proceedings of the Seventh Conference on International Language Resources and Evaluation_, Valletta, Malta, LREC, 5/2010

[1]: http://www.statmt.org/mtm12/
[2]: http://www.dfki.de/appraise/
[3]: http://www.djangoproject.com/
[4]: https://raw.github.com/cfedermann/Appraise/master/appraise/LICENSE
[5]: https://docs.djangoproject.com/en/1.4/howto/static-files/
[6]: http://pypi.python.org/pypi/flup/1.0.3.dev-20110405
