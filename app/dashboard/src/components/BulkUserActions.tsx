import {
  Alert,
  AlertDescription,
  Badge,
  Box,
  Button,
  Checkbox,
  Divider,
  Flex,
  FormControl,
  FormLabel,
  HStack,
  IconButton,
  Input,
  Menu,
  MenuButton,
  MenuItem,
  MenuList,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Select,
  Stack,
  Text,
  useDisclosure,
  useToast,
} from "@chakra-ui/react";
import {
  BoltIcon,
  CalendarDaysIcon,
  ChevronDownIcon,
  CircleStackIcon,
  NoSymbolIcon,
  TrashIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { useDashboard } from "contexts/DashboardContext";
import { FC, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { fetch } from "service/http";
import { BulkUserActionResponse, BulkUserOperation, User } from "types/User";

type BulkUserActionsProps = {
  users: User[];
  visibleCount: number;
  allVisibleSelected: boolean;
  onToggleAll: (selected: boolean) => void;
  onClear: () => void;
};

type ActionDefinition = {
  operation: BulkUserOperation;
  labelKey: string;
  kind: "status" | "data" | "days" | "delete";
  destructive?: boolean;
};

const actionDefinitions: ActionDefinition[] = [
  {
    operation: "activate",
    labelKey: "usersTable.bulkActivate",
    kind: "status",
  },
  {
    operation: "deactivate",
    labelKey: "usersTable.bulkDeactivate",
    kind: "status",
  },
  { operation: "add_data", labelKey: "usersTable.bulkAddVolume", kind: "data" },
  {
    operation: "subtract_data",
    labelKey: "usersTable.bulkSubtractVolume",
    kind: "data",
  },
  { operation: "add_days", labelKey: "usersTable.bulkAddDays", kind: "days" },
  {
    operation: "subtract_days",
    labelKey: "usersTable.bulkSubtractDays",
    kind: "days",
  },
  {
    operation: "delete",
    labelKey: "usersTable.bulkDeleteSelected",
    kind: "delete",
    destructive: true,
  },
];

const dataUnits = {
  MB: 1024 ** 2,
  GB: 1024 ** 3,
  TB: 1024 ** 4,
} as const;

const getErrorMessage = (error: unknown): string => {
  if (typeof error === "object" && error !== null) {
    const value = error as {
      data?: { detail?: unknown };
      message?: string;
    };
    if (typeof value.data?.detail === "string") return value.data.detail;
    if (value.data?.detail) return JSON.stringify(value.data.detail);
    if (value.message) return value.message;
  }
  return "Unknown error";
};

type BulkActionDialogProps = {
  action: ActionDefinition | null;
  usernames: string[];
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
};

const BulkActionDialog: FC<BulkActionDialogProps> = ({
  action,
  usernames,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const [amount, setAmount] = useState("1");
  const [unit, setUnit] = useState<keyof typeof dataUnits>("GB");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setAmount(action?.kind === "days" ? "30" : "1");
    setUnit("GB");
  }, [action, isOpen]);

  if (!action) return null;

  const numericAmount = Number(amount);
  const needsAmount = action.kind === "data" || action.kind === "days";
  const validAmount =
    !needsAmount || (Number.isFinite(numericAmount) && numericAmount > 0);

  const submit = async () => {
    if (!validAmount || isSubmitting) return;
    setIsSubmitting(true);
    try {
      const requestAmount =
        action.kind === "data"
          ? Math.round(numericAmount * dataUnits[unit])
          : action.kind === "days"
          ? Math.round(numericAmount)
          : undefined;
      const result = await fetch<BulkUserActionResponse>("/users/bulk", {
        method: "POST",
        body: {
          usernames,
          operation: action.operation,
          amount: requestAmount,
        },
      });
      toast({
        title: t("usersTable.bulkSuccess", { count: result.updated.length }),
        description: result.skipped.length
          ? t("usersTable.bulkSkipped", { count: result.skipped.length })
          : undefined,
        status: "success",
        duration: 4000,
        isClosable: true,
      });
      onSuccess();
      onClose();
    } catch (error) {
      toast({
        title: t("usersTable.bulkFailed"),
        description: getErrorMessage(error),
        status: "error",
        duration: 6000,
        isClosable: true,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={isSubmitting ? () => undefined : onClose}
      isCentered
    >
      <ModalOverlay bg="blackAlpha.700" backdropFilter="blur(5px)" />
      <ModalContent dir={i18n.dir()} mx={3} maxW="480px">
        <ModalHeader pe={12}>{t(action.labelKey)}</ModalHeader>
        <ModalCloseButton isDisabled={isSubmitting} />
        <ModalBody>
          <Stack spacing={4}>
            <Alert
              status={action.destructive ? "error" : "info"}
              variant="subtle"
              borderRadius="10px"
              borderWidth="1px"
              borderColor={action.destructive ? "red.700" : "whiteAlpha.200"}
            >
              <AlertDescription fontSize="sm" lineHeight="1.8">
                {action.destructive
                  ? t("usersTable.bulkDeleteWarning", {
                      count: usernames.length,
                    })
                  : t("usersTable.bulkAffected", { count: usernames.length })}
              </AlertDescription>
            </Alert>

            {action.kind === "data" && (
              <FormControl isRequired>
                <FormLabel>{t("usersTable.bulkVolumeAmount")}</FormLabel>
                <HStack dir="ltr">
                  <Input
                    type="number"
                    min="0.01"
                    step="0.25"
                    value={amount}
                    onChange={(event) => setAmount(event.target.value)}
                    textAlign="start"
                  />
                  <Select
                    value={unit}
                    onChange={(event) =>
                      setUnit(event.target.value as keyof typeof dataUnits)
                    }
                    w="110px"
                  >
                    <option value="MB">MB</option>
                    <option value="GB">GB</option>
                    <option value="TB">TB</option>
                  </Select>
                </HStack>
              </FormControl>
            )}

            {action.kind === "days" && (
              <FormControl isRequired>
                <FormLabel>{t("usersTable.bulkDaysAmount")}</FormLabel>
                <Input
                  type="number"
                  min="1"
                  step="1"
                  value={amount}
                  onChange={(event) => setAmount(event.target.value)}
                  dir="ltr"
                />
              </FormControl>
            )}
          </Stack>
        </ModalBody>
        <ModalFooter gap={2} flexWrap="wrap">
          <Button variant="ghost" onClick={onClose} isDisabled={isSubmitting}>
            {t("cancel")}
          </Button>
          <Button
            colorScheme={action.destructive ? "red" : "primary"}
            onClick={submit}
            isLoading={isSubmitting}
            isDisabled={!validAmount}
          >
            {t("usersTable.bulkConfirm")}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

type ExpiredCleanupDialogProps = {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
};

const ExpiredCleanupDialog: FC<ExpiredCleanupDialogProps> = ({
  isOpen,
  onClose,
  onSuccess,
}) => {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const [days, setDays] = useState("30");
  const [matches, setMatches] = useState<string[]>([]);
  const [isChecking, setIsChecking] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const cutoff = useMemo(() => {
    const value = Number(days);
    if (!Number.isFinite(value) || value < 1) return null;
    return new Date(
      Date.now() - Math.round(value) * 86400 * 1000
    ).toISOString();
  }, [days]);

  useEffect(() => {
    if (!isOpen || !cutoff) {
      setMatches([]);
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setIsChecking(true);
      try {
        const result = await fetch<string[]>("/users/expired", {
          query: { expired_before: cutoff },
          signal: controller.signal,
        });
        setMatches(result);
      } catch (error) {
        if (!controller.signal.aborted) {
          setMatches([]);
          toast({
            title: t("usersTable.bulkFailed"),
            description: getErrorMessage(error),
            status: "error",
          });
        }
      } finally {
        if (!controller.signal.aborted) setIsChecking(false);
      }
    }, 350);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [cutoff, isOpen, t, toast]);

  const removeExpired = async () => {
    if (!cutoff || matches.length === 0 || isDeleting) return;
    setIsDeleting(true);
    try {
      const removed = await fetch<string[]>("/users/expired", {
        method: "DELETE",
        query: { expired_before: cutoff },
      });
      toast({
        title: t("usersTable.cleanupSuccess", { count: removed.length }),
        status: "success",
        duration: 5000,
        isClosable: true,
      });
      onSuccess();
      onClose();
    } catch (error) {
      toast({
        title: t("usersTable.bulkFailed"),
        description: getErrorMessage(error),
        status: "error",
        duration: 6000,
        isClosable: true,
      });
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={isDeleting ? () => undefined : onClose}
      isCentered
    >
      <ModalOverlay bg="blackAlpha.700" backdropFilter="blur(5px)" />
      <ModalContent dir={i18n.dir()} mx={3} maxW="500px">
        <ModalHeader pe={12}>{t("usersTable.cleanupExpired")}</ModalHeader>
        <ModalCloseButton isDisabled={isDeleting} />
        <ModalBody>
          <Stack spacing={4}>
            <FormControl isRequired>
              <FormLabel>{t("usersTable.cleanupDays")}</FormLabel>
              <Input
                type="number"
                min="1"
                step="1"
                value={days}
                onChange={(event) => setDays(event.target.value)}
                dir="ltr"
              />
            </FormControl>
            <Alert
              status={matches.length > 0 ? "error" : "info"}
              borderRadius="10px"
              borderWidth="1px"
              borderColor={matches.length > 0 ? "red.700" : "whiteAlpha.200"}
            >
              <AlertDescription fontSize="sm" lineHeight="1.8">
                {isChecking
                  ? t("usersTable.cleanupChecking")
                  : t("usersTable.cleanupMatches", { count: matches.length })}
              </AlertDescription>
            </Alert>
            <Text color="gray.400" fontSize="xs" lineHeight="1.8">
              {t("usersTable.cleanupPermanent")}
            </Text>
          </Stack>
        </ModalBody>
        <ModalFooter gap={2} flexWrap="wrap">
          <Button variant="ghost" onClick={onClose} isDisabled={isDeleting}>
            {t("cancel")}
          </Button>
          <Button
            colorScheme="red"
            leftIcon={<TrashIcon width="18px" aria-hidden="true" />}
            onClick={removeExpired}
            isLoading={isDeleting}
            isDisabled={isChecking || matches.length === 0 || !cutoff}
          >
            {t("usersTable.cleanupConfirm", { count: matches.length })}
          </Button>
        </ModalFooter>
      </ModalContent>
    </Modal>
  );
};

export const BulkUserActions: FC<BulkUserActionsProps> = ({
  users,
  visibleCount,
  allVisibleSelected,
  onToggleAll,
  onClear,
}) => {
  const { t, i18n } = useTranslation();
  const actionDialog = useDisclosure();
  const cleanupDialog = useDisclosure();
  const [action, setAction] = useState<ActionDefinition | null>(null);
  const { refetchUsers } = useDashboard();
  const usernames = users.map((user) => user.username);

  const openAction = (definition: ActionDefinition) => {
    setAction(definition);
    actionDialog.onOpen();
  };

  const success = () => {
    onClear();
    refetchUsers();
  };

  return (
    <>
      <Flex
        dir={i18n.dir()}
        mt={4}
        px={{ base: 3, md: 4 }}
        py={3}
        minW={0}
        align="center"
        justify="space-between"
        gap={3}
        wrap="wrap"
        borderRadius="12px"
        bg="rgba(15, 23, 42, .62)"
        borderWidth="1px"
        borderColor={
          users.length > 0 ? "rgba(45, 212, 191, .3)" : "whiteAlpha.100"
        }
      >
        <HStack spacing={3} minW={0} flexWrap="wrap">
          <Checkbox
            isChecked={allVisibleSelected}
            isIndeterminate={users.length > 0 && !allVisibleSelected}
            onChange={(event) => onToggleAll(event.target.checked)}
            colorScheme="teal"
          >
            <Text fontSize="sm" fontWeight="700">
              {allVisibleSelected
                ? t("usersTable.deselectAll")
                : t("usersTable.selectAll", { count: visibleCount })}
            </Text>
          </Checkbox>
          <Badge
            px={2.5}
            py={1}
            borderRadius="full"
            bg={users.length > 0 ? "rgba(45, 212, 191, .12)" : "whiteAlpha.50"}
            color={users.length > 0 ? "teal.200" : "gray.400"}
            textTransform="none"
          >
            {t("usersTable.selectedCount", { count: users.length })}
          </Badge>
        </HStack>

        <HStack spacing={2} flexWrap="wrap" justify="flex-end">
          <Button
            size="sm"
            variant="outline"
            color="red.200"
            borderColor="red.800"
            leftIcon={<TrashIcon width="17px" aria-hidden="true" />}
            onClick={cleanupDialog.onOpen}
            _hover={{ bg: "rgba(239, 68, 68, .1)", borderColor: "red.600" }}
          >
            {t("usersTable.cleanupExpired")}
          </Button>

          {users.length > 0 && (
            <Menu placement="bottom-end">
              <MenuButton
                as={Button}
                size="sm"
                colorScheme="teal"
                rightIcon={<ChevronDownIcon width="16px" aria-hidden="true" />}
              >
                {t("usersTable.bulkActions")}
              </MenuButton>
              <MenuList
                dir={i18n.dir()}
                bg="#111827"
                borderColor="whiteAlpha.200"
                minW="230px"
              >
                <MenuItem
                  icon={<BoltIcon width="17px" aria-hidden="true" />}
                  onClick={() => openAction(actionDefinitions[0])}
                >
                  {t(actionDefinitions[0].labelKey)}
                </MenuItem>
                <MenuItem
                  icon={<NoSymbolIcon width="17px" aria-hidden="true" />}
                  onClick={() => openAction(actionDefinitions[1])}
                >
                  {t(actionDefinitions[1].labelKey)}
                </MenuItem>
                <Divider borderColor="whiteAlpha.100" />
                <MenuItem
                  icon={<CircleStackIcon width="17px" aria-hidden="true" />}
                  onClick={() => openAction(actionDefinitions[2])}
                >
                  {t(actionDefinitions[2].labelKey)}
                </MenuItem>
                <MenuItem
                  icon={<CircleStackIcon width="17px" aria-hidden="true" />}
                  onClick={() => openAction(actionDefinitions[3])}
                >
                  {t(actionDefinitions[3].labelKey)}
                </MenuItem>
                <MenuItem
                  icon={<CalendarDaysIcon width="17px" aria-hidden="true" />}
                  onClick={() => openAction(actionDefinitions[4])}
                >
                  {t(actionDefinitions[4].labelKey)}
                </MenuItem>
                <MenuItem
                  icon={<CalendarDaysIcon width="17px" aria-hidden="true" />}
                  onClick={() => openAction(actionDefinitions[5])}
                >
                  {t(actionDefinitions[5].labelKey)}
                </MenuItem>
                <Divider borderColor="whiteAlpha.100" />
                <MenuItem
                  icon={<TrashIcon width="17px" aria-hidden="true" />}
                  color="red.300"
                  onClick={() => openAction(actionDefinitions[6])}
                >
                  {t(actionDefinitions[6].labelKey)}
                </MenuItem>
              </MenuList>
            </Menu>
          )}

          {users.length > 0 && (
            <IconButton
              size="sm"
              variant="ghost"
              aria-label={t("usersTable.deselectAll")}
              icon={<XMarkIcon width="18px" aria-hidden="true" />}
              onClick={onClear}
            />
          )}
        </HStack>
      </Flex>

      <BulkActionDialog
        action={action}
        usernames={usernames}
        isOpen={actionDialog.isOpen}
        onClose={actionDialog.onClose}
        onSuccess={success}
      />
      <ExpiredCleanupDialog
        isOpen={cleanupDialog.isOpen}
        onClose={cleanupDialog.onClose}
        onSuccess={success}
      />
    </>
  );
};
