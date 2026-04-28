import { Users } from "lucide-react";

interface SocialProofCardProps {
  users: number;
}

export function SocialProofCard({ users }: SocialProofCardProps) {
  return (
    <div className="flex flex-col items-center justify-center space-y-3 mt-6 p-4 bg-primary/5 rounded-xl border border-primary/10">
      <div className="flex items-center space-x-2 text-sm font-bold text-primary">
        <Users className="w-5 h-5" />
        <span>Join {users.toLocaleString()} other farmers</span>
      </div>
      <p className="text-xs text-center text-muted-foreground italic">
        "I saved my entire tomato harvest by waiting 2 extra days like the app suggested." <br/>— Ramesh, Kolar
      </p>
    </div>
  );
}
