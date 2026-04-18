package genericsClazzMethodTypeBoundsMutation;

import testing_lib.genericsClazzMethodTypeBoundsMutation.GenericsClazzMethodTypeBoundsMutation;

public class Main extends GenericsClazzMethodTypeBoundsMutation {

	public static void main(String[] args) {
		GenericsClazzMethodTypeBoundsMutation constr = new GenericsClazzMethodTypeBoundsMutation();
		constr.<Integer>method1();
	}

	@Override
	public <T extends Integer> void method1() {

	}
}
