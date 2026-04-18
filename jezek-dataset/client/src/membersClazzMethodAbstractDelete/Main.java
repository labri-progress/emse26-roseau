package membersClazzMethodAbstractDelete;

import testing_lib.membersClazzMethodAbstractDelete.MembersClazzMethodAbstractDelete;

public class Main extends MembersClazzMethodAbstractDelete {

	@Override
	public void method1() {

	}

	public static void main(String[] args) {
		MembersClazzMethodAbstractDelete x = new Main();
		x.method1(); // <-- key: invokevirtual resolved against MembersClazzMethodAbstractDelete
	}

}
