<h1 id="appraise_evaluation_system">Appraise Evaluation System</h1>

<p>Current release used to run the evaluation of the <a href="http://www.statmt.org/wmt15/">Tenth Workshop on Statistical Machine Translation 2015</a>. It has also been used for WMT 2014 and 2013. Second major release in time for the <a href="http://www.statmt.org/mtm12/">Seventh MT Marathon 2012</a> which took place September 3-8, 2012 in Edinburgh, Scotland. Initial import into GitHub on Oct 23, 2011. First versions of this software appeared in summer 2008...</p>

<h2 id="wmt15">WMT15</h2>

<p>Rolling out things for this year's WMT15... Stay tuned for updates &mdash; Evaluation campaign at <a href="http://www.appraise.cf/">http://appraise.cf/</a></p>

<h2 id="wmt14">WMT14</h2>

<p>Follow <code>#WMT14</code> on <a href="https://twitter.com/cfedermann/">https://twitter.com/cfedermann/</a> &mdash; Evaluation campaign at <a href="http://www.appraise.cf/">http://appraise.cf/</a></p>

<p>For research group registration details or problems drop me a note via email: <code>cfedermann [at] gmail [dot] com</code></p>

<h2 id="update">Update</h2>

<p><strong>2014-03-19</strong> User changeable passwords and new action menu in navigation bar; go to <a href="http://www.appraise.cf/password/">http://www.appraise.cf/password/</a> when logged in to change the password for your Appraise account. You can also use the lovely new user action menu on the top right of the navigation bar ("Admin", of course, only visible to some):</p>

<p><img src="https://github.com/cfedermann/Appraise/raw/master/images/Appraise-User-Menu-Navbar.png" /></p>

<p><strong>2014-03-18</strong><blockquote class="twitter-tweet" lang="en"><p>Finally! <a href="https://twitter.com/search?q=%23WMT14&amp;src=hash">#WMT14</a> evaluation campaign is live! <a href="http://t.co/XaZ1Cfkqsk">http://t.co/XaZ1Cfkqsk</a> -- <a href="http://t.co/DrzOY2w8KG">http://t.co/DrzOY2w8KG</a></p>&mdash; Christian Federmann (@cfedermann) <a href="https://twitter.com/cfedermann/statuses/446001314485399552">March 18, 2014</a></blockquote> <script async src="//platform.twitter.com/widgets.js" charset="utf-8"></script></p>

<p>There's a new release of Appraise for use in the WMT '14; see the new Django app inside <code>appraise.wmt14</code> for more details.  This version also integrates with <a href="http://www.mturk.com/">Amazon's Mechanical Turk</a>, allowing to collect even more manual annotations.</p>

<h2 id="overview">Overview</h2>

<p>Appraise is an open-source tool for manual evaluation of Machine Translation output. Appraise allows to collect human judgments on translation output, implementing annotation tasks such as</p>

<ol>
<li>translation quality checking;</li>
<li>ranking of translations;</li>
<li>error classification;</li>
<li>manual post-editing.</li>
</ol>

<p>It features an extensible XML import/output format and can easily be adapted to new annotation tasks. The next version of Appraise will also include automatic computation of inter-annotator agreements allowing quick access to evaluation results.</p>

<p>Appraise is available under <a href="https://raw.github.com/cfedermann/Appraise/master/appraise/LICENSE">an open, BSD-style license</a>.</p>

<h2 id="how_does_it_look_like">How does it look like?</h2>

<p>You can see <a href="http://www.appraise.cf/">a deployed version of Appraise here</a>. If you want to play around with it, you will need an account in order to login to the system. I&#8217;ll be happy to create an account for you, just drop me an email <code>cfedermann [at] gmail [dot] com</code>.</p>

<h2 id="system_requirements">System Requirements</h2>

<p>Appraise is based on the <a href="http://www.djangoproject.com/">Django framework</a>, version 1.3 or newer. You will need <strong>Python 2.7</strong> to run it locally. For deployment, a FastCGI compatible web server such as <strong>lighttpd</strong> is required.</p>

<h2 id="quickstart_instructions">Quickstart Instructions</h2>

<p>Assuming you have already installed Python and Django, you can clone a local copy of Appraise using the following command; you can change the folder name <code>Appraise-Software</code> to anything you like.</p>

<pre><code>$ git clone git://github.com/cfedermann/Appraise.git Appraise-Software
...
</code></pre>

<p>After having cloned the GitHub project, you have to initialise Appraise. This is a two-step process:</p>

<ol>
<li><p>Initialise the SQLite database:</p>

<pre><code>$ cd Appraise-Software/appraise
$ python manage.py syncdb
...
</code></pre></li>
<li><p>Collect static files and copy them into <code>Appraise-Software/appraise/static-files</code>. Answer <code>yes</code> when asked whether you want to overwrite existing files.</p>

<pre><code>$ python manage.py collectstatic
...
</code></pre>

<p>More information on handling of static files in Django 1.3+ is <a href="https://docs.djangoproject.com/en/1.4/howto/static-files/">available here</a>.</p></li>
</ol>

<p>Finally, you can start up your local copy of Django using the <code>runserver</code> command:</p>

<pre><code>$ python manage.py runserver
</code></pre>

<p>You should be greeted with the following output from your terminal:</p>

<pre><code>Validating models...

0 errors found
Django version 1.3.1, using settings 'appraise.settings'
Development server is running at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
</code></pre>

<p>Point your browser to <a href="http://127.0.0.1:8000/appraise/">http://127.0.0.1:8000/appraise/</a> and there it is&#8230;</p>

<h3 id="add_users">Add users</h3>

<p>Users can be added <a href="http://127.0.0.1:8000/appraise/admin/auth/user/add/">here</a>.</p>

<h3 id="add_evaluation_tasks">Add evaluation tasks</h3>

<p>Evaluation tasks can be created
<a href="http://127.0.0.1:8000/appraise/admin/evaluation/evaluationtask/add/">here</a>.</p>

<p>You need an XML file in proper format to upload a task; an example file can be found in
examples/sample-ranking-task.xml .</p>

<h2 id="deployment_with_lighttpd">Deployment with lighttpd</h2>

<p>You will need to create a customised <code>start-server.sh</code> script inside <code>Appraise-Software/appraise</code>. There is a <code>.sample</code> file available in this folder which should help you get started quickly. In a nutshell, you have to uncomment and edit the last two lines:</p>

<pre><code># /path/to/bin/python manage.py runfcgi host=127.0.0.1 port=1234 method=threaded pidfile=$DJANGO_PID
</code></pre>

<p>The first line tells Django to start up in FastCGI mode, binding to hostname <code>127.0.0.1</code> and port <code>1234</code> in our example, running a <code>threaded</code> server and writing the process ID to the file <code>$DJANGO_PID</code>. The <code>.pid</code> files will be used by <code>stop-server.sh</code> to properly shutdown Appraise.</p>

<p>Using Django&#8217;s <code>manage.py</code> with the <code>runfcgi</code> command requires you to also install <code>flup</code> into the <code>site-packages</code> folder of your Python installation. It is available <a href="http://pypi.python.org/pypi/flup/1.0.3.dev-20110405">from here</a>.</p>

<pre><code># /path/to/sbin/lighttpd -f /path/to/lighttpd/etc/appraise.conf
</code></pre>

<p>The second line starts up the <code>lighttd</code> server using an appropriate configuration file <code>appraise.conf</code>. Have a look at <code>Appraise-Software/examples/appraise-lighttpd.conf</code> to create your own.</p>

<p>Once the various <code>/path/to/XYZ</code> settings are properly configured, you should be able to launch Appraise in production mode.</p>

<h2 id="references">References</h2>

<p>If you use Appraise in your research, please cite the MT Marathon 2012 paper:</p>

<p><strong>Christian Federmann</strong>
Appraise: An Open-Source Toolkit for Manual Evaluation of Machine Translation Output
In <em>The Prague Bulletin of Mathematical Linguistics volume 98</em>, Prague, Czech Republic, 9/2012</p>

<h3 id="bibtex">BibTex</h3>

<pre><code>@Article{mtm12_appraise,
  author =  {Christian Federmann},
  title =   {Appraise: An Open-Source Toolkit for Manual Evaluation of Machine Translation Output},
  journal = {The Prague Bulletin of Mathematical Linguistics},
  volume =  {98},
  pages =   {25--35},
  year =    {2012},
  address = {Prague, Czech Republic},
  month =   {September}
}
</code></pre>

<p>A previous version of Appraise had been published at LREC 2010:</p>

<p><strong>Christian Federmann</strong>
Appraise: An Open-Source Toolkit for Manual Phrase-Based Evaluation of Translations
In <em>Proceedings of the Seventh Conference on International Language Resources and Evaluation</em>, Valletta, Malta, LREC, 5/2010</p>
