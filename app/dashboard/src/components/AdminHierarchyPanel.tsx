import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Button,
  Card,
  FormControl,
  FormLabel,
  HStack,
  Input,
  SimpleGrid,
  Skeleton,
  Stack,
  Text,
  useToast,
} from "@chakra-ui/react";
import useGetUser from "hooks/useGetUser";
import { FC, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "react-query";
import { fetch } from "service/http";
import { HierarchyAdminNode } from "types/Admin";
import { formatBytes } from "utils/formatByte";

const GIB = 1024 ** 3;

type FlatNode = HierarchyAdminNode & { visualDepth: number };

const flatten = (nodes: HierarchyAdminNode[], visualDepth = 0): FlatNode[] =>
  nodes.flatMap((node) => [
    { ...node, visualDepth },
    ...flatten(node.children || [], visualDepth + 1),
  ]);

const errorText = (error: any) => {
  const detail = error?.data?.detail || error?.response?._data?.detail || error?.message;
  return typeof detail === "object" ? detail.message || detail.code : detail;
};

export const AdminHierarchyPanel: FC = () => {
  const toast = useToast();
  const queryClient = useQueryClient();
  const { userData } = useGetUser();
  const [amounts, setAmounts] = useState<Record<number, string>>({});
  const query = useQuery<HierarchyAdminNode[], Error>(
    "admin-hierarchy-tree",
    () => fetch("/admin-management/tree"),
    { refetchInterval: 15000 }
  );
  const nodes = useMemo(() => flatten(query.data || []), [query.data]);

  const action = useMutation(
    ({ node, operation, amount }: { node: FlatNode; operation: "grant" | "reclaim" | "suspend" | "resume"; amount?: number }) => {
      if (operation === "grant" || operation === "reclaim") {
        return fetch(`/admin-management/${node.username}/credit/${operation}`, {
          method: "POST",
          body: {
            amount,
            idempotency_key: `${operation}-${node.id}-${crypto.randomUUID()}`,
          },
        });
      }
      return fetch(`/admin-management/${node.username}/${operation}`, {
        method: "POST",
        body: operation === "suspend" ? { reason_id: 1, include_subtree: true } : undefined,
      });
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries("admin-hierarchy-tree");
        queryClient.invalidateQueries("admin-management");
        queryClient.invalidateQueries("account-summary");
        toast({ title: "عملیات با موفقیت انجام شد", status: "success", duration: 3000 });
      },
      onError: (error) => { toast({ title: "عملیات انجام نشد", description: errorText(error), status: "error", duration: 5000 }); },
    }
  );

  if (query.isLoading) return <Skeleton h="190px" borderRadius="18px" mb={5} />;
  if (query.isError) return <Alert status="error" mb={5}><AlertIcon />درخت مدیریتی دریافت نشد.</Alert>;

  return (
    <Card mb={5} p={{ base: 4, md: 5 }} bg="#111d17" color="gray.100" borderWidth="1px" borderColor="#33483b" borderRadius="18px" boxShadow="panel">
      <Box mb={4}>
        <Text as="h2" fontSize="lg" fontWeight="800">ساختار سلسله‌مراتبی</Text>
        <Text color="gray.400" fontSize="sm" mt={1}>نقش، وضعیت حساب و اعتبار قابل‌انتقال هر شاخه.</Text>
      </Box>
      <Stack spacing={2}>
        {nodes.map((node) => {
          const canAct = node.id !== userData.id && (userData.role === "OWNER" || node.parent_admin_id === userData.id);
          const amount = Number(amounts[node.id] || 0);
          return (
            <Box key={node.id} p={3} ps={{ base: 3, md: `${12 + node.visualDepth * 24}px` }} bg="rgba(255,255,255,.025)" borderWidth="1px" borderColor="whiteAlpha.200" borderRadius="12px">
              <SimpleGrid columns={{ base: 1, xl: canAct ? 3 : 2 }} gap={3} alignItems="center">
                <Box minW={0}>
                  <HStack flexWrap="wrap">
                    <Text fontWeight="750" dir="ltr" overflowWrap="anywhere">{node.username}</Text>
                    <Badge colorScheme={node.role === "OWNER" ? "purple" : node.role === "SUPER_ADMIN" ? "cyan" : "gray"}>{node.role.replace("_", " ")}</Badge>
                    <Badge colorScheme={node.account_status === "ACTIVE" ? "green" : "orange"}>{node.account_status}</Badge>
                  </HStack>
                  <Text mt={1} color="gray.400" fontSize="xs">عمق {node.visualDepth} · اعتبار: {node.available_traffic === null ? "نامحدود" : String(formatBytes(node.available_traffic))}</Text>
                </Box>
                <HStack spacing={3} fontSize="xs" color="gray.300" flexWrap="wrap">
                  <Text>مصرف: {formatBytes(node.own_spend)}</Text>
                  <Text>واگذارشده: {formatBytes(node.delegated_traffic)}</Text>
                  <Text>API: {node.external_api_enabled ? "فعال" : "خاموش"}</Text>
                </HStack>
                {canAct && (
                  <Stack direction={{ base: "column", md: "row" }} align={{ md: "end" }} spacing={2}>
                    <FormControl maxW={{ md: "145px" }}>
                      <FormLabel fontSize="xs" mb={1}>اعتبار (GiB)</FormLabel>
                      <Input minH="44px" type="number" min={0.01} step={0.01} dir="ltr" value={amounts[node.id] || ""} onChange={(event) => setAmounts((current) => ({ ...current, [node.id]: event.target.value }))} />
                    </FormControl>
                    <Button minH="44px" size="sm" colorScheme="green" isDisabled={!amount} isLoading={action.isLoading} onClick={() => action.mutate({ node, operation: "grant", amount: Math.round(amount * GIB) })}>واگذاری</Button>
                    <Button minH="44px" size="sm" variant="outline" isDisabled={!amount} isLoading={action.isLoading} onClick={() => action.mutate({ node, operation: "reclaim", amount: Math.round(amount * GIB) })}>بازپس‌گیری</Button>
                    <Button minH="44px" size="sm" colorScheme={node.account_status === "ACTIVE" ? "orange" : "green"} variant="ghost" isLoading={action.isLoading} onClick={() => action.mutate({ node, operation: node.account_status === "ACTIVE" ? "suspend" : "resume" })}>{node.account_status === "ACTIVE" ? "تعلیق شاخه" : "رفع تعلیق"}</Button>
                  </Stack>
                )}
              </SimpleGrid>
            </Box>
          );
        })}
      </Stack>
    </Card>
  );
};
