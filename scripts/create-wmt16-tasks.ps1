$python = "C:\Python27\Python.exe"
$cwd = "C:\Users\chrife\Source\Repos\Appraise\scripts"
$ranking_task = [System.IO.Path]::Combine($cwd, "wmt_ranking_task.py")

$batch_no = $args[0]
$source = $args[1]
$target = $args[2]
$plaindir = $args[3]
$outdir = $args[4]
$testid = $args[5]

echo "Valid testid settings = 'newstest2016', 'it-test2016'";

$pair = "$source-$target"
$filename = $pair + "-batch" + $batch_no + ".xml"
$outfile = [System.IO.Path]::Combine($outdir, $pair, $filename)

$language_map = @{
  'en' = 'eng';
  'cs' = 'cze';
  'de' = 'deu';
  'fi' = 'fin';
  'ru' = 'rus';
  'ro' = 'ron';
  'tr' = 'tur';
  'bg' = 'bul';
  'es' = 'esn';
  'eu' = 'eus';
  'nl' = 'nld';
  'pt' = 'ptb';
}

$src_file = [System.IO.Path]::Combine($plaindir, "sources", $testid + "-" + $source + $target + "-src." + $source)
$ref_file = [System.IO.Path]::Combine($plaindir, "references", $testid + "-" + $source + $target + "-ref." + $target)
$tgt_files = [System.IO.Path]::Combine($plaindir, "system-outputs", $testid, $pair, $testid + ".*." + $pair)
$outfolder = [System.IO.Path]::Combine($plaindir, "maxlen30", $source + "-" + $target)

$_ = [System.IO.Directory]::CreateDirectory($outdir)
$_ = [System.IO.Directory]::CreateDirectory([System.IO.Path]::Combine($outdir, $pair))
$_ = [System.IO.Directory]::CreateDirectory($outfolder)

C:\Python27\Python.exe ($ranking_task) ($outfile) ($src_file) ($ref_file) ($tgt_files) -source $language_map[$source] -target $language_map[$target] -maxlen 30 -save ($outfolder)
