"use client";

import { 
  Table, 
  TableBody, 
  TableCell, 
  TableHead, 
  TableHeader, 
  TableRow 
} from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Search, Loader2 } from "lucide-react";
import { useAtomValue } from "jotai";
import { adminUsersQueryAtom } from "@/atoms/admin/admin-query.atoms";
import { useState, useMemo } from "react";
import { useDebouncedValue } from "@/hooks/use-debounced-value";

export default function AdminUsersPage() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 500);

  const queryAtom = useMemo(() => adminUsersQueryAtom(page, pageSize, debouncedSearch), [page, pageSize, debouncedSearch]);
  const { data, isLoading } = useAtomValue(queryAtom);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(e.target.value);
    setPage(1); // Reset to first page on search
  };

  const handleNextPage = () => {
    if (data && page * pageSize < data.total) {
      setPage(page + 1);
    }
  };

  const handlePrevPage = () => {
    if (page > 1) {
      setPage(page - 1);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight text-white">Users</h2>
        <p className="text-neutral-400 mt-2">Manage and monitor user activity across the platform.</p>
      </div>

      <Card className="bg-neutral-900 border-neutral-800">
        <CardHeader className="pb-4 border-b border-neutral-800">
          <div className="flex items-center justify-between">
            <CardTitle className="text-white">All Users</CardTitle>
            <div className="relative w-64">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-neutral-500" />
              <Input 
                placeholder="Search by email..." 
                value={search}
                onChange={handleSearchChange}
                className="pl-9 bg-neutral-950 border-neutral-800 text-white placeholder:text-neutral-500"
              />
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader className="bg-neutral-950 border-b border-neutral-800">
              <TableRow className="hover:bg-transparent border-neutral-800">
                <TableHead className="text-neutral-400">User ID</TableHead>
                <TableHead className="text-neutral-400">Name</TableHead>
                <TableHead className="text-neutral-400">Email</TableHead>
                <TableHead className="text-neutral-400">Created At</TableHead>
                <TableHead className="text-neutral-400">Last Active</TableHead>
                <TableHead className="text-neutral-400 text-right">Total Reqs</TableHead>
                <TableHead className="text-neutral-400 text-right">Total Convs</TableHead>
                <TableHead className="text-neutral-400">Avg Response</TableHead>
                <TableHead className="text-neutral-400 text-right">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-8">
                    <Loader2 className="h-6 w-6 animate-spin text-blue-500 mx-auto" />
                  </TableCell>
                </TableRow>
              ) : data?.items.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={9} className="text-center py-8 text-neutral-500">
                    No users found
                  </TableCell>
                </TableRow>
              ) : (
                data?.items.map((user) => (
                  <TableRow key={user.id} className="border-neutral-800 hover:bg-neutral-800/50">
                    <TableCell className="font-mono text-xs text-neutral-300">
                      {user.id.substring(0, 8)}...
                    </TableCell>
                    <TableCell className="font-medium text-white">{user.name || "-"}</TableCell>
                    <TableCell className="text-neutral-400">{user.email}</TableCell>
                    <TableCell className="text-neutral-400">
                      {new Date(user.joined_date).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-neutral-400">
                      {user.last_active ? new Date(user.last_active).toLocaleString() : "-"}
                    </TableCell>
                    <TableCell className="text-right text-neutral-300">
                      {user.total_requests.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-right text-neutral-300">
                      {user.total_conversations.toLocaleString()}
                    </TableCell>
                    <TableCell className="text-neutral-400">Mocked</TableCell>
                    <TableCell className="text-right">
                      <Badge variant={user.status === "Active" ? "default" : "secondary"} className={
                        user.status === "Active" 
                          ? "bg-green-500/10 text-green-500 hover:bg-green-500/20" 
                          : "bg-neutral-800 text-neutral-400 hover:bg-neutral-800"
                      }>
                        {user.status}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
          
          <div className="p-4 border-t border-neutral-800 flex items-center justify-between text-sm text-neutral-400">
            <div>
              Showing {data?.total ? Math.min((page - 1) * pageSize + 1, data.total) : 0} to{" "}
              {data?.total ? Math.min(page * pageSize, data.total) : 0} of {data?.total || 0} users
            </div>
            <div className="flex items-center gap-2">
              <button 
                onClick={handlePrevPage} 
                disabled={page <= 1}
                className="px-3 py-1 border border-neutral-800 rounded hover:bg-neutral-800 disabled:opacity-50"
              >
                Previous
              </button>
              <button 
                onClick={handleNextPage} 
                disabled={!data || page * pageSize >= data.total}
                className="px-3 py-1 border border-neutral-800 rounded hover:bg-neutral-800 disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
