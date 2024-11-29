def call(String url) {
    // Load the Python script and requirements
    def scanner = libraryResource 'main.py'
    writeFile file: 'main.py', text: scanner

    def requirements = libraryResource 'requirements.txt'
    writeFile file: 'requirements.txt', text: requirements

    if (isUnix()) {
        sh '''
            python3 -m venv venv
            source venv/bin/activate
            which python3
            pip3 install -r requirements.txt
            python3 -m pip list
        '''

        // Run the Python script with the URL
        sh "source venv/bin/activate && python3 main.py '${url}'"

        // Verify files in the directory
        sh 'ls -l'
    } else if (isWindows()) {
        bat '''
            python -m venv venv
            .\\venv\\Scripts\\activate.bat && pip install -r requirements.txt
        '''

        // Run the Python script with the URL
        bat ".\\venv\\Scripts\\activate.bat && python main.py \"${url}\""
    }
}
