#!/usr/bin/env python

import pypandoc
import cherrypy
from cherrypy.lib import static

from pathlib import Path
from tempfile import NamedTemporaryFile
import urllib.request
import validators

"""
Configure the CherryPy server
"""
config = {
    'global' : {
        'server.socket_host' : '10.0.1.5',
        'server.socket_port' : 8080
    }
}

"""
Main class:
"""
class PandocService(object):
	"""
	Here's the HTML input form
	"""
	@cherrypy.expose
	def index(self):
		return """<html>
  	        <head>
  	        	<title>Document Converter</title>
  	        	<style>
  	        		body {margin:5% 10%;}
  	        		label {padding-right:1em;}
  	        		h3 {border-bottom: 1px solid lightgrey; padding-top:1em;}
  	        	</style>
  	        	<script>
  	        		function togglePaths(_checked) {
  	        			document.getElementById('bib_path').disabled = _checked ? false : true;
  	        			document.getElementById('bib_file').disabled = _checked ? false : true;
  	        			document.getElementById('csl_path').disabled = _checked ? false : true;
  	        		}
  	        		function toggleBibOnly(_checked) {
  	        			document.getElementById('bib_path').disabled = _checked ? false : true;
  	        		}
  	        	</script>
  	        </head>
  	        <body>
		    <h1>Document Converter</h1>
		    	<h3>Web Form</h3>
	            <form method="post" action="convert" enctype="multipart/form-data">
	              <div id="file">
	              	<h4>Choose File <code>in_file</code></h4>
	              	<input type="file" name="in_file" />
	              </div>
	              <div id="output">
	              	<h4>Output Format <code>output</code></h4>
	              	<input type="radio" name="output" value="pdf" checked />
	              	<label for="output"><code>pdf</code></label>
	              	<input type="radio" name="output" value="tex" />
	              	<label for="output"><code>tex</code></label>
	              	<input type="radio" name="output" value="docx" />
	       			<label for="output"><code>docx</code></label>
	              	<input type="radio" name="output" value="html" />
	              	<label for="output"><code>html</code></label>
	              	<input type="radio" name="output" value="rtf" />
	              	<label for="output"><code>rtf</code></label>
	              </div>
	              <div id="options">
	              	<h4>Options</h4>
	              	<input type="checkbox" name="standalone" value="True" checked />
	              	<label for="standalone"><code>standalone</code></label>
	              	<input type="checkbox" name="xelatex" value="True" checked />
	              	<label for="xelatex"><code>xelatex</code></label>
	              </div>
	              <div id="filters">
	              	<h4>Filters</h4>
	              	<input type="checkbox" name="crossref" value="crossref" checked />
	              	<label for="crossref"><code>crossref</code></label>
	              	<input type="checkbox" name="citeproc" value="citeproc" onchange="togglePaths(this.checked)" />
	              	<label for="citeproc"><code>citeproc</code></label>
	              	<input type="checkbox" name="natbib" value="natbib" onchange="togglePaths(this.checked)" />
	              	<label for="natbib"><code>natbib</code></label>
	              	<input type="checkbox" name="biblatex" value="biblatex" onchange="togglePaths(this.checked)" />
	              	<label for="biblatex"><code>biblatex</code></label><br />
	              	<label for="bib_path"><code>bib_path</code>:</label>
	              	<input type="text" size="80" id="bib_path" name="bib_path" value="https://raw.githubusercontent.com/tweedyflanigan/zotero/master/Library.bib" /> 
	              	<strong>or</strong> 
	              	<input type="file" id="bib_file" name="bib_file" onchange="toggleBibOnly(this.checked)" /><br />
	              	<label for="csl_path"><code>csl_path</code>:</label>
	              	<input type="text" size="80" id="csl_path" name="csl_path" value="https://github.com/citation-style-language/styles/raw/master/chicago-author-date-16th-edition.csl" /> 
	              	[<a href="https://github.com/citation-style-language/styles" target="_blank">?</a>]
	              </div>
	              <div id="submit">
	              	<button type="submit" style="margin-top:2em;">Convert!</button>
	              </div>
	            </form>
	            <h5>Notes:</h5>
	            <ul><li><code>bib_path</code> and <code>csl_path</code> can be given as paths on the server or as URLs</li></ul>
	            <h3>Command Line</h3>
	            <code>curl -F 'in_file=@</code><em><small>input file</small></em><code>' -F '</code><em><small>args</small></em><code>' http://192.168.1.13/convert -o </code><em><small>output file</small></em>
	            <h5>Example</h5>
	            <code>
	            	curl -F 'in_file=@/path/to/file.md' -F 'output=html' -F 'standalone=True' -F 'crossref=True' -F 'citeproc=True' -F 'bib_path=http://url.to/file.bib' -F 'csl_path='http://url.to/file.csl' http://192.168.1.13:8080/convert -o Output.html
	            </code>
	            <h5>Notes:</h5> 
	            <ul><li>Omit unwanted options rather than passing them to cURL as <code>False</code></li>
	            <li>Make sure the extension of <code>Output.html</code> matches the value given to <code>output</output></li></ul>
	          </body>
	        </html>"""
	
	"""
	Do the conversion and return the converted file
	"""
	@cherrypy.expose
	def convert(self, **kwargs):
		# Let's assign our variables

		# Initialize data containers
		data = None
		bib_data = None

		# file_in:
		try:
			data = kwargs['in_file'].file.read() # Read in the uploaded file
			short_name = Path(kwargs['in_file'].filename).stem # Get the file's name (stem) to use again later
		except:
			return "No input file received"

		# bib_file:
		try:
			bib_data = kwargs['bib_file'].file.read() # Read in the bibliography file (if it exists)
		except:
			bib_file = None

		# output format:
		try:
			to_format = kwargs['output'] # Set output type from passed argument
		except:
			to_format = 'html' # Set html as output type if not passed

		# remaining variables (set to None if not passed):		
		try:
			standalone = kwargs['standalone']
		except:
			standalone = None
		
		try:
			xelatex = kwargs['xelatex']
		except:
			xelatex = None
		
		try:
			crossref = kwargs['crossref']
		except:
			crossref = None
		
		try:
			citeproc = kwargs['citeproc']
		except:
			citeproc = None
			
		try:
			natbib = kwargs['natbib']
		except:
			natbib = None

		try:
			biblatex = kwargs['biblatex']
		except:
			biblatex = None
		
		try:
			bib_path = kwargs['bib_path']
		except:
			bib_path = None
		
		try:
			csl_path = kwargs['csl_path']
		except:
			csl_path = None
		
		# Copy the uploaded file to /tmp
		tmp_in = NamedTemporaryFile(suffix='.md',mode="w+b")
		tmp_in.write(data)
		tmp_in.seek(0)
		
		# Handle the .bib path as file, or URL or path, but only if using pandoc-citeproc
		# (We only need to do this for the .bib because pandoc handles .csl URLs fine by itself)
		if citeproc:
			if bib_data is not None:
				tmp_bib = NamedTemporaryFile(suffix='.bib',mode="w+b")
				tmp_bib.write(bib_data)
				tmp_bib.seek(0)
				bib_path = tmp_bib.name
			if bib_path is not None:
				if validators.url(bib_path):
					# Download and use the .bib file
					tmp_bib = NamedTemporaryFile(suffix='.bib',mode='w+b')
					tmp_bib.write(urllib.request.urlopen(bib_path).read())
					tmp_bib.seek(0)
					bib_path = tmp_bib.name

		# Add in options as arguments
		pdoc_args = []
		if standalone:
			pdoc_args.append('--standalone')
		if biblatex:
			pdoc_args.append('--biblatex')
		if natbib:
			pdoc_args.append('--natbib')
		if xelatex:
			pdoc_args.append('--pdf-engine=xelatex')

		# Add in filters and their associated arguments
		pdoc_filters = []
		if crossref:
			pdoc_filters.append('pandoc-crossref')
		if citeproc:
			pdoc_filters.append('pandoc-citeproc')
		if bib_path is not None:
			pdoc_args.append('--bibliography="'+bib_path+'"')
		if csl_path:
			pdoc_args.append('--csl="'+csl_path+'"')

		# generate the file using pandoc
		tmp_out = NamedTemporaryFile(suffix='.'+to_format)
		try:
			out = pypandoc.convert_file(tmp_in.name, to_format, outputfile=tmp_out.name, extra_args=pdoc_args)
			assert out == ""
		except:
			return "Error running pandoc"
		return static.serve_file(tmp_out.name, content_type='application/x-download', disposition='attachment', name=short_name+'.'+to_format)

"""
Run the CherryPy server
"""
if __name__ == '__main__':
	# Do this as a daemon instead of in console
	from cherrypy.process.plugins import Daemonizer
	d = Daemonizer(cherrypy.engine)
	d.subscribe()

	cherrypy.quickstart(PandocService(), '/', config)
