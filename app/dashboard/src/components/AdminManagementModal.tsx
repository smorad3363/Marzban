import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Button,
  FormControl,
  FormLabel,
  HStack,
  Input,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Select,
  Spinner,
  Table,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
  useToast,
  VStack,
} from "@chakra-ui/react";
import { FC, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "react-query";
import { useTranslation } from "react-i18next";
import { fetch } from "service/http";

type AdminRole = "owner" | "reseller";
type AdminStatus = "active" | "suspended";

type AdminRecord = {
  username: string;
  is_sudo: boolean;
  role: AdminRole;
  status: AdminStatus;
  permissions: Record<string, unknown>;
};

type AdminForm = {
  username: string;
  password: string;
  role: AdminRole;
  status: AdminStatus;
  permissions: Record<string, unknown>;
};

type AdminManagementModalProps = {
  isOpen: boolean;
  onClose: () => void;
};

const emptyForm: AdminForm = {
  username: "",
  password: "",
  role: "reseller",
  status: "active",
  permissions: {},
};

const adminQueryKey = ["admin-management"];

const getErrorMessage = (error: unknown, fallback: string) => {
  if (typeof error === "object" && error !== null) {
    const response = (error as { data?: { detail?: unknown } }).data;
    if (typeof response?.detail === "string") {
      return response.detail;
    }
  }
  return fallback;
};

export const AdminManagementModal: FC<AdminManagementModalProps> = ({
  isOpen,
  onClose,
}) => {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [form, setForm] = useState<AdminForm | null>(null);
  const [editingUsername, setEditingUsername] = useState<string | null>(null);
  const [deletingAdmin, setDeletingAdmin] = useState<AdminRecord | null>(null);

  const admins = useQuery<AdminRecord[], Error>(
    adminQueryKey,
    () => fetch("/admins"),
    { enabled: isOpen }
  );

  const finishMutation = async (message: string) => {
    await queryClient.invalidateQueries(adminQueryKey);
    setForm(null);
    setEditingUsername(null);
    toast({
      title: message,
      status: "success",
      isClosable: true,
      position: "top",
      duration: 3000,
    });
  };

  const saveAdmin = useMutation(
    async (values: AdminForm) => {
      const payload: Record<string, unknown> = {
        role: values.role,
        status: values.status,
        is_sudo: values.role === "owner",
        permissions: values.permissions,
      };
      if (values.password) {
        payload.password = values.password;
      }
      if (editingUsername) {
        return fetch(`/admin/${encodeURIComponent(editingUsername)}`, {
          method: "PUT",
          body: payload,
        });
      }
      return fetch("/admin", {
        method: "POST",
        body: { ...payload, username: values.username },
      });
    },
    {
      onSuccess: () =>
        finishMutation(
          editingUsername
            ? t("adminManagement.updated")
            : t("adminManagement.created")
        ),
      onError: (error) => {
        toast({
          title: getErrorMessage(error, t("adminManagement.saveError")),
          status: "error",
          isClosable: true,
          position: "top",
        });
      },
    }
  );

  const deleteAdmin = useMutation(
    (admin: AdminRecord) =>
      fetch(`/admin/${encodeURIComponent(admin.username)}`, {
        method: "DELETE",
      }),
    {
      onSuccess: async () => {
        setDeletingAdmin(null);
        await finishMutation(t("adminManagement.deleted"));
      },
      onError: (error) => {
        toast({
          title: getErrorMessage(error, t("adminManagement.deleteError")),
          status: "error",
          isClosable: true,
          position: "top",
        });
      },
    }
  );

  const startCreate = () => {
    setEditingUsername(null);
    setForm({ ...emptyForm, permissions: {} });
  };

  const startEdit = (admin: AdminRecord) => {
    setEditingUsername(admin.username);
    setForm({
      username: admin.username,
      password: "",
      role: admin.role,
      status: admin.status,
      permissions: admin.permissions || {},
    });
  };

  const closeModal = () => {
    setForm(null);
    setEditingUsername(null);
    setDeletingAdmin(null);
    onClose();
  };

  return (
    <>
      <Modal isCentered isOpen={isOpen} onClose={closeModal} size="4xl">
        <ModalOverlay bg="blackAlpha.300" backdropFilter="blur(10px)" />
        <ModalContent mx="3">
          <ModalHeader pt={6}>
            <HStack justify="space-between" pr={8}>
              <Box>
                <Text>{t("adminManagement.title")}</Text>
                <Text mt={1} fontSize="sm" fontWeight="normal" color="gray.500">
                  {t("adminManagement.description")}
                </Text>
              </Box>
              <Button
                size="sm"
                colorScheme="blue"
                onClick={startCreate}
              >
                {t("adminManagement.create")}
              </Button>
            </HStack>
          </ModalHeader>
          <ModalCloseButton mt={3} />
          <ModalBody pb={6}>
            {form && (
              <Box
                mb={5}
                p={4}
                borderWidth="1px"
                borderColor="primary.200"
                borderRadius="xl"
                bg="primary.50"
                _dark={{ bg: "whiteAlpha.50", borderColor: "primary.700" }}
              >
                <Text fontWeight="semibold" mb={4}>
                  {editingUsername
                    ? t("adminManagement.editTitle", {
                        username: editingUsername,
                      })
                    : t("adminManagement.createTitle")}
                </Text>
                <VStack spacing={4} align="stretch">
                  <HStack align="start" spacing={4} flexWrap="wrap">
                    <FormControl isRequired={!editingUsername} flex="1 1 190px">
                      <FormLabel fontSize="sm">
                        {t("adminManagement.username")}
                      </FormLabel>
                      <Input
                        size="sm"
                        value={form.username}
                        isDisabled={!!editingUsername}
                        onChange={(event) =>
                          setForm({ ...form, username: event.target.value })
                        }
                      />
                    </FormControl>
                    <FormControl isRequired={!editingUsername} flex="1 1 190px">
                      <FormLabel fontSize="sm">
                        {editingUsername
                          ? t("adminManagement.passwordOptional")
                          : t("adminManagement.password")}
                      </FormLabel>
                      <Input
                        size="sm"
                        type="password"
                        value={form.password}
                        onChange={(event) =>
                          setForm({ ...form, password: event.target.value })
                        }
                      />
                    </FormControl>
                    <FormControl flex="1 1 140px">
                      <FormLabel fontSize="sm">
                        {t("adminManagement.role")}
                      </FormLabel>
                      <Select
                        size="sm"
                        value={form.role}
                        onChange={(event) =>
                          setForm({
                            ...form,
                            role: event.target.value as AdminRole,
                          })
                        }
                      >
                        <option value="owner">
                          {t("adminManagement.owner")}
                        </option>
                        <option value="reseller">
                          {t("adminManagement.reseller")}
                        </option>
                      </Select>
                    </FormControl>
                    <FormControl flex="1 1 140px">
                      <FormLabel fontSize="sm">
                        {t("adminManagement.status")}
                      </FormLabel>
                      <Select
                        size="sm"
                        value={form.status}
                        onChange={(event) =>
                          setForm({
                            ...form,
                            status: event.target.value as AdminStatus,
                          })
                        }
                      >
                        <option value="active">
                          {t("adminManagement.active")}
                        </option>
                        <option value="suspended">
                          {t("adminManagement.suspended")}
                        </option>
                      </Select>
                    </FormControl>
                  </HStack>
                  <HStack justify="end">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setForm(null)}
                    >
                      {t("cancel")}
                    </Button>
                    <Button
                      size="sm"
                      colorScheme="blue"
                      isLoading={saveAdmin.isLoading}
                      isDisabled={
                        !form.username || (!editingUsername && !form.password)
                      }
                      onClick={() => saveAdmin.mutate(form)}
                    >
                      {t("adminManagement.save")}
                    </Button>
                  </HStack>
                </VStack>
              </Box>
            )}

            {admins.isLoading ? (
              <HStack justify="center" py={10}>
                <Spinner />
              </HStack>
            ) : admins.isError ? (
              <Alert status="error" borderRadius="lg">
                <AlertIcon />
                {t("adminManagement.loadError")}
              </Alert>
            ) : (
              <Box borderWidth="1px" borderRadius="xl" overflowX="auto">
                <Table size="sm">
                  <Thead>
                    <Tr>
                      <Th>{t("adminManagement.username")}</Th>
                      <Th>{t("adminManagement.role")}</Th>
                      <Th>{t("adminManagement.status")}</Th>
                      <Th textAlign="right">
                        {t("adminManagement.actions")}
                      </Th>
                    </Tr>
                  </Thead>
                  <Tbody>
                    {(admins.data || []).map((admin) => (
                      <Tr key={admin.username}>
                        <Td fontWeight="semibold">{admin.username}</Td>
                        <Td>
                          <Badge colorScheme={admin.role === "owner" ? "blue" : "purple"}>
                            {t(`adminManagement.${admin.role}`)}
                          </Badge>
                        </Td>
                        <Td>
                          <Badge
                            colorScheme={
                              admin.status === "active" ? "green" : "orange"
                            }
                          >
                            {t(`adminManagement.${admin.status}`)}
                          </Badge>
                        </Td>
                        <Td>
                          <HStack justify="end">
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => startEdit(admin)}
                            >
                              {t("adminManagement.edit")}
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              colorScheme="red"
                              onClick={() => setDeletingAdmin(admin)}
                            >
                              {t("delete")}
                            </Button>
                          </HStack>
                        </Td>
                      </Tr>
                    ))}
                  </Tbody>
                </Table>
                {!admins.data?.length && (
                  <Text py={8} textAlign="center" color="gray.500">
                    {t("adminManagement.empty")}
                  </Text>
                )}
              </Box>
            )}
          </ModalBody>
          <ModalFooter pt={0}>
            <Button size="sm" variant="outline" onClick={closeModal}>
              {t("adminManagement.close")}
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      <Modal
        isCentered
        isOpen={!!deletingAdmin}
        onClose={() => setDeletingAdmin(null)}
        size="sm"
      >
        <ModalOverlay bg="blackAlpha.300" backdropFilter="blur(10px)" />
          <ModalContent mx="3">
            <ModalHeader>
              {t("adminManagement.deleteTitle")}
            </ModalHeader>
            <ModalBody>
              {t("adminManagement.deletePrompt", {
                username: deletingAdmin?.username,
              })}
            </ModalBody>
            <ModalFooter>
              <Button
                onClick={() => setDeletingAdmin(null)}
              >
                {t("cancel")}
              </Button>
              <Button
                ml={3}
                colorScheme="red"
                isLoading={deleteAdmin.isLoading}
                onClick={() =>
                  deletingAdmin && deleteAdmin.mutate(deletingAdmin)
                }
              >
                {t("delete")}
              </Button>
            </ModalFooter>
          </ModalContent>
      </Modal>
    </>
  );
};
