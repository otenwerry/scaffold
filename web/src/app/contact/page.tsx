import Header from "../../components/Header";
import { Card } from "@/components/ui/card";
import { CardTitle } from "@/components/ui/card";
import { CardContent } from "@/components/ui/card";
import Link from "next/link";

export default function Contact() {
  return (
    <div className="flex flex-col items-center justify-center">
      <Header />

      <div className="wireframe-bg"></div>

      <main className="relative z-10 flex flex-col items-center justify-start h-screen px-4 pt-20">
        <Card>
          <CardTitle className="text-4xl font-bold text-gray-900 leading-relaxed text-center">Get Started</CardTitle>
          <CardContent className="text-lg md:text-lg text-gray-600 max-w-3xl mx-auto leading-relaxed text-left italic">
              1. Once download is complete, open the installer by clicking on the downloaded file. <br />
              2. Drag Scaffold into the Applications folder next to it, as well as your Dock next to other apps. <br />
              3. Then, open System Settings and navigate to Privacy & Security in the side bar. <br />
              4. Add Scaffold to Accessibility, Input Monitoring, and Screen & System Audio Recording.
            </CardContent>
        </Card>
      </main>
    </div>
  );
}