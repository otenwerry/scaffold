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

      <main className="relative z-10 flex flex-col items-center justify-start px-4 pt-20 md:pt-25 pb-8">
        <Card className="justify-center items-center">
          <CardTitle className="text-4xl font-bold text-gray-900 leading-relaxed text-center">Thanks for trying out Scaffold!</CardTitle>
          <CardContent className="text-lg md:text-lg text-gray-800 max-w-3xl mx-auto leading-relaxed text-left">
            <strong>1.</strong><Button className="futuristic-button text-white text-lg mr-1 ml-1 px-2 py-1 h-auto max-w-md text-center">
             <a href="https://github.com/otenwerry/scaffold/releases/download/beta1.0.10/Scaffold.dmg" download>
              Download
            </a>
          </Button> the latest version here (macOS only)<br /> 
            <div className="flex flex-col md:items-start md:flex-row my-2 gap-8">
              <div className="flex flex-col md:my-2 my-0">
              <span><strong>2. Open</strong></span>
              <Image src="/images/download.png" alt="Download" width={250} height={200} className="rounded-lg w-full md:w-64 h-auto" />
              <span className="text-sm text-gray-500 mt-2 text-center md:text-left">Open <strong>Scaffold.dmg</strong> from Downloads</span>
              </div>
              <div className="flex flex-col my-2">
              <span><strong>3. Install</strong></span>
              <Image src="/images/drag1.png" alt="Drag" width={250} height={200} className="rounded-lg w-full md:w-64 h-auto" />
              <span className="text-sm text-gray-500 mt-2 text-center md:text-left">Drag <strong>Scaffold</strong> to Applications</span>
              </div>
              <div className="flex flex-col my-2">
                <span><strong>4. Launch</strong></span>
                <Image src="/images/launch.png" alt="Drag" width={250} height={200} className="rounded-lg w-full md:w-64 h-auto" />
                <span className="text-sm text-gray-500 mt-2 text-center md:text-left">Open <strong>Scaffold</strong> from Applications </span>
              </div>
            </div>
            <Image src="/images/w_logo.png" alt="Icon" width={16} height={16} className="inline" /> should appear in your menu bar at the top of your screen
            <div className="flex justify-start my-2">
              <Image src='/images/tray1.png' alt="Tray" width={307} height={100} className="rounded-lg w-full md:w-64 h-auto" />
            </div>
            <strong>5. </strong> To start or stop asking a question, use the shortcut <strong> Option (⌥) + Space </strong>, or click <Image src="/images/w_logo.png" alt="Icon" width={16} height={16} className="inline" /> and press <strong> &lsquo;Start Asking&rsquo; </strong> <br /> 
            <div className="h-4">
            </div>
            <strong>6. </strong> Once you ask a question, Scaffold will prompt you for: <br />
            
            <div className="flex flex-row my-2 gap-8">
            <div className="flex flex-col">
            <span> Microphone Permissions</span>
            <Image src="/images/mic1.png" alt="Download" width={250} height={200} className="rounded-lg" />
            <span className="text-xs text-gray-500 mt-2">Required so Scaffold can hear what you say</span>
            </div>
            <div className="flex flex-col ">
            <span>Screen & System Audio Recording Permissions</span>
            <Image src="/images/sys_perm.png" alt="Drag" width={460} height={200} className="rounded-lg" />
            <span className="text-xs text-gray-500 mt-2 max-w-md">Optional but highly recommended so Scaffold can see your screen momentarily when you start asking a question. Screenshots aren&apos;t saved</span>
            </div>
          
            </div>
            If you&apos;d rather not let Scaffold see your screen, you can leave the latter turned off &mdash; it&apos;s still useful just as a conversation partner while you have eyes on your work. <br />
          </CardContent>
        </Card>
      </main>
      <Footer />
    </div>
  );
}