import React from "react";
import axios from "axios";
import ReactModal from "react-modal";
import { format } from "date-fns";

import { GrTrash, GrUser } from "react-icons/gr";

import { formatCurrency } from "@/lib/util";

setTimeout(() => {
  if (document.getElementById("customers") !== null) {
    ReactModal.setAppElement("#customers");
  }
}, 1000);

const CustomerModal = ({
  activeCustomer,
  isOpen,
  closeModal,
  deleteCustomer,
}: {
  activeCustomer: any;
  isOpen: any;
  closeModal: any;
  deleteCustomer: any;
}) => {
  const [loading, setLoading] = React.useState(false);
  const [data, setData] = React.useState({ accounts: [], fileContent: "" });
  const [error, setError] = React.useState(null);

  const [showPic, setShowPic] = React.useState(false);

  React.useEffect(() => {
    setLoading(true);
    setError(null);
    setData({ accounts: [], fileContent: "" });

    if (!activeCustomer?.customerId) return;

    axios
      .get(
        `${process.env.NEXT_PUBLIC_SCBANK_DATA_API}/customer-api/api/customers/${activeCustomer?.customerId}`
      )
      .then((response) => {
        setData(response?.data);
      })
      .catch((error) => {
        setError(error?.message);
      })
      .finally(() => {
        setLoading(false);
      });
  }, [activeCustomer]);

  const deleteCustomerHandler = () => {
    const deleteConfirmation = confirm("Are you sure you want to delete?");

    if (!deleteConfirmation) return;

    deleteCustomer(activeCustomer?.customerId);

    closeModal();

    setShowPic(false);
  };

  const toggleProfilePic = () => {
    setShowPic(!showPic);
  };

  const close = () => {
    setShowPic(false);

    closeModal();
  };

  return (
    <ReactModal
      isOpen={isOpen}
      onRequestClose={close}
      contentLabel="Customer Details"
      className="react-modal"
      overlayClassName="react-modal-overlay"
    >
      <div style={{ minHeight: 300 }}>
        {loading ? (
          <div
            style={{
              color: "green",
              minHeight: 300,
              width: "100%",
              display: "grid",
              placeItems: "center",
            }}
          >
            Loading...
          </div>
        ) : error ? (
          <div
            style={{
              color: "orangered",
              minHeight: 300,
              width: "100%",
              display: "grid",
              placeItems: "center",
            }}
          >
            {error}
          </div>
        ) : (
          <div style={{}}>
            <div style={{ overflowY: "auto", marginTop: 30, maxHeight: 500 }}>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1.5fr",

                  fontWeight: "bolder",
                  color: "#444",
                  fontSize: 16,
                }}
              >
                <div>Customer ID: {activeCustomer?.customerId}</div>

                <div>Full Name: {activeCustomer?.name}</div>
              </div>
              <div>
                {data?.accounts?.map((element: any) => {
                  return (
                    <div
                      key={element?.accountId}
                      style={{
                        backgroundColor: "#f3e5f5",
                        padding: 10,
                        marginTop: 15,
                        borderRadius: 5,
                      }}
                    >
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "1fr 1fr 1fr",
                          fontWeight: "bolder",
                          color: "darkblue",
                        }}
                      >
                        <div>Account ID: {element?.accountId}</div>
                        <div>Type: {element?.accountType}</div>
                        <div>Balance: {formatCurrency(element?.balance)}</div>
                        {/* <div>{element?.currency}</div> */}
                      </div>

                      <div
                        style={{
                          border: "2px white solid",
                          marginTop: 15,
                          padding: 10,
                        }}
                      >
                        <div
                          style={{
                            display: "grid",
                            gridTemplateColumns:
                              ".75fr 1.5fr 1.5fr 2fr 1fr 1fr",

                            fontWeight: "bold",
                          }}
                        >
                          <div>ID</div>
                          <div>Transaction Date</div>
                          <div>Amount</div>
                          <div>Description</div>
                          <div>Type</div>
                          <div>Balance</div>
                        </div>

                        {element?.transactions?.map((transaction: any) => {
                          return (
                            <div
                              style={{
                                display: "grid",
                                gridTemplateColumns:
                                  ".75fr 1.5fr 1.5fr 2fr 1fr 1fr",

                                marginTop: 10,
                              }}
                              key={transaction?.txnId}
                            >
                              <div>{transaction?.txnId}</div>
                              <div>
                                {format(
                                  new Date(transaction?.date),
                                  "dd-MMM-yyyy hh:mm"
                                )}
                              </div>
                              <div>{formatCurrency(transaction?.amount)}</div>
                              <div>{transaction?.description}</div>
                              <div>{transaction?.type}</div>
                              <div>
                                {formatCurrency(transaction?.balanceAfterTxn)}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
      <div
        onClick={close}
        style={{
          position: "absolute",
          top: 15,
          right: 15,
          cursor: "pointer",
          fontSize: 18,
          fontWeight: "bolder",
          display: "grid",
          placeItems: "center",
          backgroundColor: "#ddd",
          borderRadius: "50%",
          width: 26,
          height: 26,
          padding: 2,
        }}
      >
        x
      </div>

      <div
        style={{
          position: "absolute",
          top: 25,
          right: 100,
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gridGap: 20,
          color: "#72308f",
          fontSize: 18,
        }}
      >
        <div>
          {activeCustomer?.allowDelete === "Y" ? (
            <GrTrash
              style={{
                cursor: "pointer",
              }}
              onClick={deleteCustomerHandler}
            />
          ) : null}
        </div>
        <div>
          <GrUser
            style={{
              cursor: "pointer",
            }}
            onClick={toggleProfilePic}
          />
        </div>
      </div>

      {showPic && (
        <div
          style={{
            position: "absolute",
            top: 50,
            left: 0,

            display: "grid",
            placeItems: "center",

            width: "100%",
            height: "calc(100% - 50px)",
            backgroundColor: "white",
          }}
        >
          <img
            src={`data:image/png;base64, ${data?.fileContent}`}
            alt={activeCustomer?.name}
            style={{
              width: 200,
              border: "1px lightgrey solid",
              display: "block",
            }}
          />
        </div>
      )}
    </ReactModal>
  );
};

export default CustomerModal;
