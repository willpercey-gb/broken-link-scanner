def call(String url) {
    def scanner = libraryResource 'main.py'
    writeFile file: 'main.py', text: scanner

    def requirements = libraryResource 'requirements.txt'
    writeFile file: 'requirements.txt', text: requirements


    if (isUnix()) {
        sh 'virtualenv venv'
        sh 'source venv/bin/activate'
        sh 'pip install -r requirements.txt'
        sh "python3 main.py ${url}"
    } else if (isWindows()) {
        bat 'virtualenv venv'
        bat '.\\venv\\Scripts\\activate.bat && pip install -r requirements.txt'
        bat ".\\venv\\Scripts\\activate.bat && python main.py ${url}"
    }
}
