# Pin the real upstream controller, rather than the ansible-rulebook runner.
FROM quay.io/ansible/eda-server@sha256:871f17fe92a7d20fbb05aa4877482378f3be58ec3fbb44980c7c5aafe3750dbb
COPY --chmod=755 entrypoint.sh /app/aax-entrypoint.sh
ENTRYPOINT ["/app/aax-entrypoint.sh"]
CMD ["api"]
