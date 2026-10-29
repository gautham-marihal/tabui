import { getEnvVariables } from "@/lib/get-env-variables";
import { NextResponse, NextRequest } from "next/server";

export async function POST(request: NextRequest) {
  const body = await request.json(); // Parse JSON body

  const userPassCode = body?.userPassCode;
  const agentId = body?.agentId;
  const { allowedOriginsToCallAPI } = getEnvVariables(agentId);

  const corsHeaders = {
    headers: {
      "Access-Control-Allow-Origin": allowedOriginsToCallAPI || "",
      "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization",
    },
  };

  if (!userPassCode) {
    return NextResponse.json(
      { error: "Need 'userPassCode' key in request JSON" },
      { status: 400, ...corsHeaders }
    );
  } else {
    const element = userAccounts.find((element) => {
      return element?.userPasscode === userPassCode;
    });

    return NextResponse.json(
      { userName: element?.name, authSucess: element?.name ? true : false },
      { status: 200, ...corsHeaders }
    );
  }
}

const userAccounts = [
  { id: 100, name: "Sreekanth M E", userPasscode: "34753311" },
  { id: 200, name: "Ashwin Prabhu", userPasscode: "APJ*^KJ)DE%AP" },
  { id: 300, name: "Binny Mathew", userPasscode: "BMHJVYU^#)(FGBM" },
  { id: 400, name: "Vineeth Nayak", userPasscode: "VNG%&$$)34VN" },
  {
    id: 500,
    name: "Weerathungage Sumudu Saman",
    userPasscode: "VSS*%AV$j87VSS",
  },
  { id: 600, name: "Sanjay Pai", userPasscode: "SP*&59@&((&$SP" },
  { id: 700, name: "Ajay Saraf", userPasscode: "AS$*KJGYU$^%AS" },
  { id: 800, name: "Vinod Srinivasan", userPasscode: "VS&75879&%$(VS" },
  { id: 900, name: "Indra Wijaya Kusuma", userPasscode: "IWK(*&#@()!!IWK" },
];
