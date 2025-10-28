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
          <CardTitle className="text-4xl font-bold text-gray-900 leading-relaxed text-center">Contact</CardTitle>
          <CardContent className="text-lg md:text-lg text-gray-600 max-w-3xl mx-auto leading-relaxed text-left">
          Say hello at our <Link href="https://forms.gle/5MTK88AkJx8NLUVt8" target="_blank" className="text-blue-500 hover:text-blue-700">form</Link>! Feedback/bugs/questions are all welcome. 
          </CardContent>
        </Card>
      </main>
    </div>
  );
}