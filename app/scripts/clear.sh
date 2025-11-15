rm -rf build dist
rm -rf Scaffold.dmg
rm -rf Scaffold-app.zip
rm -rf /Applications/Scaffold.app

tccutil reset Microphone com.scaffold.tutor-dev
tccutil reset ScreenCapture com.scaffold.tutor-dev
tccutil reset ListenEvent com.scaffold.tutor-dev
tccutil reset Accessibility com.scaffold.tutor-dev
