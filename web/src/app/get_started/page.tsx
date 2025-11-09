import Header from "../../components/Header";
import { Card, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import Footer from "../../components/Footer";
import { CardDescription } from "@/components/ui/card";
import Image from "next/image";

export default function GetStarted() {
  return (
    <div className="flex flex-col items-center justify-center">
      <Header />

      <div className="wireframe-bg"></div>

      <main className="relative z-10 flex flex-col items-center justify-start h-screen px-4 pt-20 md:pt-25">
        <Card className="justify-center items-center">
          <CardTitle className="text-4xl font-bold text-gray-900 leading-relaxed text-center">Get Started</CardTitle>
          <CardContent className="text-lg md:text-lg text-gray-800 max-w-3xl mx-auto leading-relaxed text-left">
            <strong>1.</strong> <Button className="futuristic-button text-white text-lg ml-1 mr-1 px-2 py-1 h-auto max-w-md text-center">
            <a href="https://github.com/otenwerry/scaffold/releases/download/v1.0.3/Scaffold.dmg" download>
              Download
            </a>
          </Button> the latest version of Scaffold<br /> 
            <div className="flex flex-row  my-2 gap-8">
              <div className="flex flex-col my-2">
              <span><strong>2.</strong> Open</span>
              <Image src="/images/download.png" alt="Download" width={250} height={200} className="rounded-lg" />
              </div>
              <div className="flex flex-col my-2">
              <span><strong>3.</strong> Install</span>
              <Image src="/images/drag1.png" alt="Drag" width={250} height={200} className="rounded-lg" />
              </div>
              <div className="flex flex-col my-2">
                <span><strong>4.</strong> Launch</span>
              </div>
            </div>
            
            You can also drag it into your dock on the bottom of your screen with your other apps for easy access. <br />
            4. Open the app and <Image src="/images/w_logo.png" alt="Icon" width={16} height={16} className="inline" /> should appear in your menu bar at the top of your screen.
            <div className="flex justify-center my-2">
              <Image src='/images/tray.png' alt="Tray" width={307} height={100} className="rounded-lg" />
            </div>
            5. To start or stop asking a question, use the shortcut <strong> Command (⌘) + Shift (⇧) + Space </strong>, or click the logo and press <strong> &lsquo;Start Asking&rsquo; </strong> in the menu bar. <br /> 
            6. Once you ask a question, Scaffold will prompt you for Microphone permissions and Screen & System Audio Recording permissions, so that it can hear you and see your screen.
            <div className="flex gap-4 my-2 justify-center">
              <Image src='/images/mic.png' alt="Permissions" width={307} height={100} className="rounded-lg" /> 
              <Image src='/images/sys.png' alt="Permissions2" width={307} height={100} className="rounded-lg" />
            </div>
            If you&apos;d rather not let Scaffold see your screen, you can leave the latter turned off &mdash; it&apos;s still useful just as a conversation partner while you have eyes on your work.
          </CardContent>
        </Card>
      </main>
      <Footer />
    </div>
  );
}