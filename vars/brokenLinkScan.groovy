def call(String url) {
    def scanner = libraryResource 'main.py'
    writeFile file: 'main.py', text: scanner

    def requirements = libraryResource 'requirements.txt'
    writeFile file: 'requirements.txt', text: requirements


    if (isUnix()) {
        sh '''
            source venv/bin/activate
            which python3
            pip3 install -r requirements.txt
            python3 -m pip list
            python3 main.py https://developer-docs.wacom.com
        '''

    } else if (isWindows()) {
        bat 'virtualenv venv'
        bat '.\\venv\\Scripts\\activate.bat && pip install -r requirements.txt'
        bat ".\\venv\\Scripts\\activate.bat && python main.py ${url}"
    }
}
