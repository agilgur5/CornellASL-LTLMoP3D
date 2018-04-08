from flask import Flask, request, render_template, jsonify, send_file, session
import os, sys, datetime, uuid, threading, zipfile

sys.path.append(os.path.join(os.sep, 'LTLMoP','src','lib')) # add lib to path
import specCompiler

UPLOAD_FOLDER = 'uploads'

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT' # not actually a secret since no need for authentication

def validate_ext(filename, ext):
  """helper to validate file extension"""
  return '.' in filename and filename.rsplit('.', 1)[1] == ext

# deletes files older than 24 hours
def deleteOldFiles():
  dir_to_search = app.config['UPLOAD_FOLDER']
  for dirpath, dirnames, filenames in os.walk(dir_to_search):
    for file in filenames:
      curpath = os.path.join(dirpath, file)
      file_modified = datetime.datetime.fromtimestamp(os.path.getmtime(curpath))
      if datetime.datetime.now() - file_modified > datetime.timedelta(hours=5):
        os.remove(curpath)

# creates session if one does not already exist
def createSession():
  session.permanent = False # session should stop after browser close
  if 'username' not in session:
    session['username'] = str(uuid.uuid4()) # create session as a random unique string
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], session['username'])) # create a directory for this session
  # delete old files asynchronously after each session creation
  threading.Thread(target=deleteOldFiles).start()

def joinToSessionDir(path):
  """helper to join path to the session directory"""
  return os.path.join(app.config['UPLOAD_FOLDER'], session['username'], path)

def saveToSession(ext):
  """helper to save an uploaded file"""
  file = request.files[ext]
  if not file or not validate_ext(file.filename, ext):
    return False
  session_key = ext + 'FilePath'  # e.g. specFilePath
  new_name = ext + '.' + ext  # e.g. spec.spec
  session[session_key] = joinToSessionDir(new_name)
  file.save(session[session_key])
  return True

# ----------------- simulator functions ------------------------------
@app.route('/simulator')
def loadSimulator():
  return render_template('/simulator.html', name='simulator')

# -------------------- spec editor functions -----------------------------

# render the spec editor
@app.route('/')
@app.route('/specEditor')
def loadSpecEditor():
  return render_template('/specEditor.html', name='specEditor')

# compiles the project via the spec file, returns log
@app.route('/specEditor/compileSpec', methods=['POST'])
def compileSpec():
  createSession()
  saveToSession('regions')
  saveToSession('spec')
  sc = specCompiler.SpecCompiler()
  sc.loadSpec(session['specFilePath'])
  realizable, realizableFS, logString = sc.compile()
  # create zip of all files in the project
  with zipfile.ZipFile(joinToSessionDir(session['username'] + '.zip'), 'w') as myzip:
    myzip.write(session['regionsFilePath'], os.path.basename(session['regionsFilePath']))
    myzip.write(session['specFilePath'], os.path.basename(session['specFilePath']))
    fileName, fileExtension = os.path.splitext(session['specFilePath']) # split extension
    myzip.write(fileName + '.ltl', os.path.basename(fileName + '.ltl'))
    myzip.write(fileName + '.smv', os.path.basename(fileName + '.smv'))
    myzip.write(fileName + '.aut', os.path.basename(fileName + '.aut'))
    myzip.write(fileName + '_decomposed.regions', os.path.basename(fileName + '_decomposed.regions'))

  return jsonify({'compilerLog': logString})

# analyzes the spec and sends back the output
@app.route('/specEditor/analyzeSpec', methods=['GET'])
def analyzeSpec():
  sc = specCompiler.SpecCompiler()
  sc.loadSpec(session['specFilePath'])
  realizable, unsat, nonTrivial, to_highlight, output = sc._analyze()
  return jsonify(analyzeLog = output)

# sends the currently stored spec to the user
@app.route('/specEditor/saveSpec', methods=['GET'])
def saveSpec():
  return send_file(session['specFilePath'], as_attachment=True, mimetype='text/plain')

# sends the currently stored regions to the user
@app.route('/specEditor/saveRegions', methods=['GET'])
def saveRegions():
  return send_file(session['regionsFilePath'], as_attachment=True, mimetype='text/plain')

# sends the currently stored aut to the user
@app.route('/specEditor/saveAut', methods=['GET'])
def saveAut():
  fileName, fileExtension = os.path.splitext(session['specFilePath']) # split extension
  thepath = fileName + '.aut'
  return send_file(thepath, as_attachment=True, mimetype='text/plain')

# sends the currently stored ltl to the user
@app.route('/specEditor/saveLTL', methods=['GET'])
def saveLTL():
  fileName, fileExtension = os.path.splitext(session['specFilePath']) # split extension
  thepath = fileName + '.ltl'
  return send_file(thepath, as_attachment=True, mimetype='text/plain')

# sends the currently stored smv to the user
@app.route('/specEditor/saveSMV', methods=['GET'])
def saveSMV():
  fileName, fileExtension = os.path.splitext(session['specFilePath']) # split extension
  thepath = fileName + '.smv'
  return send_file(thepath, as_attachment=True, mimetype='text/plain')

# sends the currently stored decomposed regions to the user
@app.route('/specEditor/saveDecomposed', methods=['GET'])
def saveDecomposed():
  fileName, fileExtension = os.path.splitext(session['specFilePath']) # split extension
  thepath = fileName + '_decomposed.regions'
  return send_file(thepath, as_attachment=True, mimetype='text/plain')

# sends the currently stored zipped project to the user
@app.route('/specEditor/saveZip', methods=['GET'])
def saveZip():
  thepath = joinToSessionDir(session['username'] + '.zip')
  return send_file(thepath, as_attachment=True, mimetype='text/plain')


# ------------------------- region editor functions ------------------------


if __name__ == '__main__':
  port = int(os.environ.get('PORT', 5000))
  debug = bool(os.environ.get('DEBUG', False))
  app.run(host='0.0.0.0', port=port, debug=True)